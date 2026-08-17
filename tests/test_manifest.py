from s2st.manifest import Utterance


def test_manifest_requires_direct_s2st_fields() -> None:
    item = Utterance(
        id="a",
        source_audio="source.wav",
        target_audio="target.wav",
        reference_translation="hola",
        provenance="test",
    )
    assert item.id == "a"
    assert item.target_audio == "target.wav"

