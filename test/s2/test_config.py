import pathlib

import s2.config

p = pathlib.Path(__file__).parent


def test_load_configs(monkeypatch):
    monkeypatch.setattr(s2.config, "DEFAULT_CONFIG", {"file": "DEFAULT_CONFIG"})

    d = s2.config.load_configs(
        [
            p / "test_config1.toml",
            "this.also.works=1",
            p / "test_config2.toml",
        ]
    )

    assert d["section"]["file"].endswith("config2.toml")
    assert d["section"]["key1"] == "Value 1"
    assert d["section"]["key2"] == "Value 2"
    assert d["this"]["also"]["works"] == 1
