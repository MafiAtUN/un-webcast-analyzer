"""
Test only the transcription functionality with the fixed diarized_json format.
"""

import asyncio
from backend.services.azure_openai_client import azure_openai_client
from backend.services.audio_processor import audio_processor
import json

async def test_transcription():
    """Test transcription with diarized_json format."""

    # Small video URL
    url = "https://webtv.un.org/en/asset/k1y/k1y7kgo2oc"

    print("=" * 80)
    print("TESTING TRANSCRIPTION WITH DIARIZED_JSON")
    print("=" * 80)

    # Download audio
    print("\n1. Downloading audio...")
    audio_path = await audio_processor.download_and_extract_audio(url, "k1y7kgo2oc")
    print(f"   ✅ Downloaded: {audio_path}")

    import os
    file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
    print(f"   File size: {file_size_mb:.2f} MB")

    # Transcribe
    print("\n2. Transcribing with Azure OpenAI...")
    try:
        result = await azure_openai_client.transcribe_audio_with_diarization(audio_path)

        print("\n3. TRANSCRIPTION RESULT:")
        print("-" * 80)

        full_text = result.get('full_text', '')
        segments = result.get('segments', [])

        print(f"   Full text length: {len(full_text)} characters")
        print(f"   Number of segments: {len(segments)}")

        if segments:
            print(f"\n   ✅ SUCCESS! Got {len(segments)} segments with speaker diarization")

            # Show first 3 segments
            print(f"\n   First 3 segments:")
            for i, seg in enumerate(segments[:3]):
                print(f"\n   Segment {i+1}:")
                print(f"     Speaker: {seg.get('speaker_id', 'N/A')}")
                print(f"     Time: {seg.get('start_time', 'N/A')} - {seg.get('end_time', 'N/A')}")
                print(f"     Text: {seg.get('text', '')[:80]}...")

            # Count unique speakers
            unique_speakers = set(s.get('speaker_id', '') for s in segments)
            print(f"\n   Unique speakers: {len(unique_speakers)}")
            print(f"   Speakers: {', '.join(sorted(unique_speakers))}")

            # Show full result structure
            print(f"\n   Full result keys: {list(result.keys())}")
            print(f"   Language: {result.get('language', 'N/A')}")
            print(f"   Duration: {result.get('duration', 0)}s")

            print("\n" + "=" * 80)
            print("✅✅✅ TRANSCRIPTION WORKS PERFECTLY! ✅✅✅")
            print("=" * 80)
        else:
            print("\n   ❌ FAILED - No segments returned!")
            print(f"   Full result: {json.dumps(result, indent=2)}")

    except Exception as e:
        print(f"\n   ❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Cleanup
        if os.path.exists(audio_path):
            os.remove(audio_path)
            print(f"\n✅ Cleaned up: {audio_path}")

if __name__ == "__main__":
    asyncio.run(test_transcription())
