"""Tests for configuration data classes."""

from audit_engine.utils.config import (
    BankFingerprints,
    HeartbeatConfig,
    Paths,
    UIConfig,
    UpdateConfig,
    fingerprints,
    heartbeat,
    paths,
    ui,
    update,
)


def test_paths_defaults():
    p = Paths()
    assert p.log.endswith(".log")
    assert p.db.endswith(".db")
    assert p.log != p.db


def test_paths_singleton():
    assert paths.log.endswith(".log")
    assert paths.db.endswith(".db")


def test_bank_fingerprints():
    fp = BankFingerprints()
    assert "prospectno" in fp.idfc
    assert "svs_loan_no" in fp.equitas
    assert "jewellery1" in fp.arvog


def test_bank_fingerprints_singleton():
    assert "tare weight" in fingerprints.idfc


def test_update_config():
    uc = UpdateConfig()
    assert "DeepStacker/pdf-generator" in uc.repo
    assert "github.com" in uc.github_api


def test_update_config_singleton():
    assert update.repo == "DeepStacker/pdf-generator"


def test_ui_config():
    uc = UIConfig()
    assert uc.max_recent_files == 8


def test_ui_config_singleton():
    assert ui.max_recent_files == 8


def test_heartbeat_config():
    hc = HeartbeatConfig()
    assert hc.timeout == 120
    assert hc.interval == 15


def test_heartbeat_config_singleton():
    assert heartbeat.timeout == 120
    assert heartbeat.interval == 15
