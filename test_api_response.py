"""
Test script to check Azure OpenAI transcription API response format.
"""

import asyncio
from backend.services.azure_openai_client import azure_openai_client
from backend.services.audio_processor import audio_processor
from loguru import logger
import json

async def test_small_video():
    """Test with a small UN video to see actual API response."""

    # Small video URL (should be quick)
    url = "https://webtv.un.org/en/asset/k1y/k1y7kgo2oc"

    print("=" * 80)
    print("TESTING AZURE API RESPONSE FORMAT")
    print("=" * 80)

    # Download audio
    print("\n1. Downloading audio...")
    audio_path = await audio_processor.download_and_extract_audio(url, "k1y7kgo2oc")
    print(f"   Downloaded: {audio_path}")

    # Get file size
    import os
    file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
    print(f"   File size: {file_size_mb:.2f} MB")

    # Transcribe
    print("\n2. Transcribing with Azure OpenAI...")
    print("   Using: gpt-4o-transcribe-diarize")
    print("   Format: json")
    print("   Chunking: auto")

    try:
        with open(audio_path, "rb") as audio_file:
            result = azure_openai_client.client.audio.transcriptions.create(
                model="gpt-4o-transcribe-diarize",
                file=audio_file,
                language="en",
                response_format="json",
                chunking_strategy="auto"
            )

        print("\n3. API Response Analysis:")
        print("-" * 80)

        # Check what attributes the result has
        print("   Available attributes:")
        for attr in dir(result):
            if not attr.startswith('_'):
                print(f"     - {attr}")

        print("\n   Response Type:", type(result))

        # Try to access text
        if hasattr(result, 'text'):
            print(f"\n   ✓ Has 'text' attribute")
            print(f"     Length: {len(result.text)} characters")
            print(f"     Preview: {result.text[:200]}...")
        else:
            print("\n   ✗ No 'text' attribute")

        # Try to access segments
        if hasattr(result, 'segments'):
            print(f"\n   ✓ Has 'segments' attribute")
            print(f"     Count: {len(result.segments)}")
            if len(result.segments) > 0:
                print(f"     First segment:")
                seg = result.segments[0]
                for attr in dir(seg):
                    if not attr.startswith('_'):
                        try:
                            val = getattr(seg, attr)
                            if not callable(val):
                                print(f"       - {attr}: {val}")
                        except:
                            pass
        else:
            print("\n   ✗ No 'segments' attribute")

        # Try to access other common attributes
        for attr in ['language', 'duration', 'words', 'utterances', 'speakers']:
            if hasattr(result, attr):
                val = getattr(result, attr)
                print(f"\n   ✓ Has '{attr}': {val}")

        # Try to convert to dict
        print("\n4. Attempting to serialize to JSON:")
        try:
            if hasattr(result, 'model_dump'):
                result_dict = result.model_dump()
                print("   ✓ Using model_dump():")
                print(f"     Keys: {list(result_dict.keys())}")
                print("\n   Full response:")
                print(json.dumps(result_dict, indent=2)[:1000])
            elif hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
                print("   ✓ Using to_dict():")
                print(f"     Keys: {list(result_dict.keys())}")
            else:
                print("   ✗ No serialization method found")
        except Exception as e:
            print(f"   ✗ Serialization failed: {e}")

        print("\n" + "=" * 80)
        print("TEST COMPLETE")
        print("=" * 80)

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Cleanup
        if os.path.exists(audio_path):
            os.remove(audio_path)
            print(f"\n✓ Cleaned up: {audio_path}")

if __name__ == "__main__":
    asyncio.run(test_small_video())
