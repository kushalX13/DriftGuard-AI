"""Tests for deterministic doc retrieval."""

from pathlib import Path

import pytest

from scripts.retrieval import get_doc, get_sections, retrieve


def test_get_doc_sg_open_ssh() -> None:
    text = get_doc("sg_open_ssh")
    assert "What this means" in text
    assert "0.0.0.0/0" in text


def test_get_doc_s3_encryption() -> None:
    text = get_doc("s3_encryption")
    assert "server-side encryption" in text.lower()
    assert "How to fix" in text


def test_get_sections() -> None:
    sections = get_sections("sg_open_ssh")
    assert "What this means" in sections
    assert "Why it matters" in sections
    assert "How to fix" in sections
    assert "References" in sections
    assert "SSH" in sections["What this means"]


def test_retrieve_multiple_keys() -> None:
    out = retrieve(["sg_open_ssh", "s3_encryption"], sections_only=True)
    assert "sg_open_ssh" in out
    assert "s3_encryption" in out
    assert isinstance(out["sg_open_ssh"], dict)
    assert "What this means" in out["sg_open_ssh"]


def test_retrieve_missing_key_omitted() -> None:
    out = retrieve(["sg_open_ssh", "nonexistent_key"], sections_only=True)
    assert "sg_open_ssh" in out
    assert "nonexistent_key" not in out
