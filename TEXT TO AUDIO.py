import boto3
import os
import random
import glob
from pydub import AudioSegment


def text_to_audio(text, voice='Matthew', add_background_music=False, background_music_dir=None, output_filename=None):
    # Retrieve AWS credentials from environment variables.
    aws_access_key = "AKIA4VDBMBKDQAICBAMW"
    aws_secret_key = "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"
    aws_region =  "us-east-1"

    if not aws_access_key or not aws_secret_key:
        raise ValueError("AWS credentials are not set in the environment variables.")

    # Initialize AWS Polly client.
    polly = boto3.client(
        "polly",
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key,
        region_name=aws_region
    )

    # Synthesize speech using AWS Polly.
    try:
        polly_response = polly.synthesize_speech(
            Engine="neural",
            LanguageCode="en-US",
            VoiceId=voice,
            OutputFormat="mp3",
            Text=text
        )
    except Exception as e:
        raise Exception(f"Error calling AWS Polly: {e}")

    # Create a temporary file for the raw audio.
    if output_filename is None:
        output_filename = f"audio_{random.randint(1000,9999)}.mp3"
    raw_audio_path = f"raw_{output_filename}"

    # Write the raw audio data to a file.
    with open(raw_audio_path, "wb") as f:
        f.write(polly_response["AudioStream"].read())

    final_audio_path = output_filename

    # Overlay background music if requested.
    if add_background_music:
        if not background_music_dir:
            raise ValueError("Background music directory must be provided when add_background_music is True.")
        # Retrieve a list of MP3 files in the background music directory.
        bg_files = glob.glob(os.path.join(background_music_dir, "*.mp3"))
        if bg_files:
            selected_bg = random.choice(bg_files)
            # Load the synthesized speech and background music using pydub.
            speech = AudioSegment.from_mp3(raw_audio_path)
            background = AudioSegment.from_mp3(selected_bg)

            # Lower the background music volume by 21 dB.
            background = background - 21

            # Ensure the background music's frame rate matches the speech.
            if speech.frame_rate != background.frame_rate:
                background = background.set_frame_rate(speech.frame_rate)

            # Extend background music if it's shorter than the speech.
            if len(background) < len(speech):
                repeat_times = (len(speech) // len(background)) + 1
                background = background * repeat_times
            # Trim the background music to match the speech duration.
            background = background[:len(speech)]

            # Overlay the background music onto the speech.
            combined = speech.overlay(background, position=0)
            combined.export(final_audio_path, format="mp3")
        else:
            # If no background music files are found, fall back to raw audio.
            os.rename(raw_audio_path, final_audio_path)
    else:
        os.rename(raw_audio_path, final_audio_path)

    return final_audio_path

# Example usage:
if _name_ == "_main_":
    sample_text = str(input("Enter the text to be converted into speech here:"))
    try:
        # Update 'background_music_dir' with your actual directory path if you wish to add background music.
        audio_file = text_to_audio(
            text=sample_text,
            voice='Matthew',
            add_background_music=True,             # Set to False to disable background music.
            background_music_dir="path/to/bg/music", # Provide a valid path to a directory with MP3 files.
            output_filename="final_audio.mp3"
        )
        print(f"Generated audio file: {audio_file}")
    except Exception as e:
        print(f"Error during text-to-audio processing: {e}")