"""
Test script to check diarized_json response format.
"""

import asyncio
from backend.services.azure_openai_client import azure_openai_client
from backend.services.audio_processor import audio_processor
from loguru import logger
import json

async def test_diarized_format():
    """Test with diarized_json response format."""

    # Small video URL (should be quick)
    url = "https://webtv.un.org/en/asset/k1y/k1y7kgo2oc"

    print("=" * 80)
    print("TESTING DIARIZED_JSON RESPONSE FORMAT")
    print("=" * 80)

    # Download audio
    print("\n1. Downloading audio...")
    audio_path = await audio_processor.download_and_extract_audio(url, "k1y7kgo2oc")
    print(f"   Downloaded: {audio_path}")

    # Get file size
    import os
    file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
    print(f"   File size: {file_size_mb:.2f} MB")

    # Test different response formats
    formats_to_test = ["diarized_json", "verbose_json", "json", "text"]

    for fmt in formats_to_test:
        print(f"\n{'=' * 80}")
        print(f"TESTING FORMAT: {fmt}")
        print("=" * 80)

        try:
            with open(audio_path, "rb") as audio_file:
                print(f"\n   Calling API with:")
                print(f"   - model: gpt-4o-transcribe-diarize")
                print(f"   - response_format: {fmt}")
                print(f"   - chunking_strategy: auto")

                result = azure_openai_client.client.audio.transcriptions.create(
                    model="gpt-4o-transcribe-diarize",
                    file=audio_file,
                    language="en",
                    response_format=fmt,
                    chunking_strategy="auto"
                )

            print(f"\n   ✓ API call succeeded!")
            print(f"   Response Type: {type(result)}")

            # Check what attributes the result has
            print(f"\n   Available attributes:")
            attrs = [attr for attr in dir(result) if not attr.startswith('_')]
            for attr in attrs[:20]:  # Show first 20
                print(f"     - {attr}")

            # Try to access key attributes
            if hasattr(result, 'text'):
                print(f"\n   ✓ Has 'text' attribute")
                print(f"     Length: {len(result.text)} characters")
                print(f"     Preview: {result.text[:150]}...")

            if hasattr(result, 'segments'):
                print(f"\n   ✓ Has 'segments' attribute!")
                print(f"     Count: {len(result.segments)}")
                if len(result.segments) > 0:
                    print(f"\n     First segment details:")
                    seg = result.segments[0]
                    seg_attrs = [attr for attr in dir(seg) if not attr.startswith('_')]
                    for attr in seg_attrs:
                        try:
                            val = getattr(seg, attr)
                            if not callable(val):
                                print(f"       {attr}: {val}")
                        except:
                            pass
            else:
                print(f"\n   ✗ No 'segments' attribute")

            # Check for other relevant attributes
            for attr in ['language', 'duration', 'words', 'utterances', 'speakers', 'diarization']:
                if hasattr(result, attr):
                    val = getattr(result, attr)
                    print(f"\n   ✓ Has '{attr}': {type(val)}")
                    if isinstance(val, (list, tuple)) and len(val) > 0:
                        print(f"     First item: {val[0]}")

            # Try to serialize
            print(f"\n   Attempting to serialize:")
            try:
                if hasattr(result, 'model_dump'):
                    result_dict = result.model_dump()
                    print(f"   ✓ Serialized successfully")
                    print(f"   Keys: {list(result_dict.keys())}")
                    print(f"\n   Full JSON (first 2000 chars):")
                    json_str = json.dumps(result_dict, indent=2)
                    print(json_str[:2000])
                    if len(json_str) > 2000:
                        print(f"   ... ({len(json_str) - 2000} more characters)")
            except Exception as e:
                print(f"   ✗ Serialization failed: {e}")

        except Exception as e:
            print(f"\n   ✗ ERROR with format '{fmt}': {e}")
            import traceback
            traceback.print_exc()

    # Cleanup
    try:
        if os.path.exists(audio_path):
            os.remove(audio_path)
            print(f"\n✓ Cleaned up: {audio_path}")
    except:
        pass

    print("\n" + "=" * 80)
    print("ALL TESTS COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_diarized_format())
