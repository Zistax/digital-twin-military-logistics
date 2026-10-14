import json
import numpy as np
import pytest

from src.sim import main_sim, analyze_last_run
from src.ml import predict_cli, model_info
from src.config import config_loader, terminology_loader


@pytest.mark.parametrize("module", [main_sim, predict_cli])
@pytest.mark.parametrize(
    "value,expected", [("", 10), ("bad", 10), ("-1", 10), ("4", 4)]
)
def test_console_input_defaults_and_validation(monkeypatch, module, value, expected):
    monkeypatch.setattr("builtins.input", lambda _: value)
    assert module.ask_int("value", 10) == expected


def test_console_simulation_and_csv_analysis(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(main_sim, "load_sim_config", lambda: {})
    monkeypatch.setattr("builtins.input", lambda _: "")
    main_sim.main()
    analyze_last_run.main()
    assert "Convogli completati:" in capsys.readouterr().out
    csv = analyze_last_run.find_latest_events_csv()
    assert csv.exists()
    with pytest.raises(FileNotFoundError):
        analyze_last_run.find_latest_events_csv(tmp_path / "missing")
    with pytest.raises(FileNotFoundError):
        analyze_last_run.find_latest_events_csv(tmp_path)


def test_prediction_console_missing_model_and_success(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("builtins.input", lambda _: "")
    predict_cli.main()
    assert "ERRORE" in capsys.readouterr().out

    class Model:
        def predict_proba(self, x):
            return np.tile([0.7, 0.3], (len(x), 1))

    monkeypatch.setattr(predict_cli, "load_risk_model", lambda _: Model())
    predict_cli.main()
    assert "Risultati" in capsys.readouterr().out


def test_yaml_configs_and_model_report(tmp_path, monkeypatch):
    monkeypatch.setattr(terminology_loader, "BASE_CONF_DIR", tmp_path)
    p = tmp_path / "terminology"
    p.mkdir()
    (p / "default.yml").write_text("terminology:\n  Attack: event\n")
    mapping = terminology_loader.load_terminology()
    assert terminology_loader.translate_term("ATTACK", mapping) == "event"
    assert terminology_loader.translate_term("unknown", mapping) == "unknown"
    (p / "default.yml").write_text("terminology: []")
    with pytest.raises(ValueError):
        terminology_loader.load_terminology()
    with pytest.raises(FileNotFoundError):
        terminology_loader.load_terminology("missing")
    yaml = tmp_path / "invalid.yml"
    yaml.write_text("[]")
    with pytest.raises(ValueError):
        config_loader._load_yaml_file(yaml)
    with pytest.raises(FileNotFoundError):
        config_loader._load_yaml_file(tmp_path / "missing.yml")
    report = tmp_path / "model.report.json"
    report.write_text(json.dumps({"model_version": "v1"}))
    assert model_info.get_model_version(tmp_path / "model.pkl") == "v1"
