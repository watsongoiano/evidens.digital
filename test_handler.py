#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Valida o handler da API serverless (checkup_intelligent_v3)."""

from __future__ import annotations

import io
import json
import os
import sys
from typing import Dict, Any
from unittest.mock import Mock


def _load_handler():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    api_dir = os.path.join(root_dir, 'api')
    if api_dir not in sys.path:
        sys.path.insert(0, api_dir)

    from checkup_intelligent_v3 import handler  # type: ignore

    return handler


def _build_handler_instance(handler_cls, payload: Dict[str, Any]):
    body = json.dumps(payload).encode('utf-8')

    instance = handler_cls.__new__(handler_cls)
    instance.rfile = io.BytesIO(body)
    instance.wfile = io.BytesIO()
    instance.headers = {'Content-Length': str(len(body))}
    instance.client_address = ('127.0.0.1', 12345)
    instance.command = 'POST'
    instance.path = '/api/checkup_intelligent_v3'
    instance.request_version = 'HTTP/1.1'
    instance.server = Mock()
    instance.log_message = lambda *args, **kwargs: None

    def _send_response(status_code):
        instance._status = status_code  # type: ignore[attr-defined]

    instance.send_response = _send_response
    instance.send_header = lambda *args, **kwargs: None
    instance.end_headers = lambda: None

    return instance


def _extract_titles(recommendations):
    titles = set()
    for rec in recommendations or []:
        titulo = (rec or {}).get('titulo') or ''
        titles.add(titulo.strip().lower())
    return titles


def test_handler_includes_mental_health_and_prep():
    handler_cls = _load_handler()

    payload = {
        'idade': 30,
        'sexo': 'feminino',
        'peso': 70,
        'altura': 165,
        'pressao_sistolica': 118,
        'colesterol_total': 180,
        'hdl_colesterol': 55,
        'creatinina': 0.9,
        'comorbidades': [],
        'tabagismo': 'nunca'
    }

    handler_instance = _build_handler_instance(handler_cls, payload)
    handler_instance.do_POST()

    assert getattr(handler_instance, '_status', None) == 200

    response_body = handler_instance.wfile.getvalue().decode('utf-8')
    data = json.loads(response_body)
    titles = _extract_titles(data.get('recommendations'))

    assert 'questionário gad-7 (triagem de ansiedade)' in titles
    assert 'questionário phq-9 (triagem de depressão)' in titles
    assert 'profilaxia pré-exposição ao hiv (prep)' in titles


def test_handler_returns_prep_for_adult_men():
    handler_cls = _load_handler()

    payload = {
        'idade': 22,
        'sexo': 'masculino',
        'peso': 80,
        'altura': 175,
        'pressao_sistolica': 120,
        'colesterol_total': 190,
        'hdl_colesterol': 45,
        'creatinina': 1.0,
        'comorbidades': [],
        'tabagismo': 'nunca'
    }

    handler_instance = _build_handler_instance(handler_cls, payload)
    handler_instance.do_POST()

    assert getattr(handler_instance, '_status', None) == 200

    response_body = handler_instance.wfile.getvalue().decode('utf-8')
    data = json.loads(response_body)
    titles = _extract_titles(data.get('recommendations'))

    assert 'profilaxia pré-exposição ao hiv (prep)' in titles
