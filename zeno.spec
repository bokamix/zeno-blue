# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for ZENO desktop app."""
import os
import sys
from pathlib import Path

# Collect tiktoken data files
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

tiktoken_datas = collect_data_files('tiktoken')
tiktoken_datas += collect_data_files('tiktoken_ext')

# Collect all pydantic hidden imports
pydantic_imports = collect_submodules('pydantic')

a = Analysis(
    ['zeno.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('frontend/dist', 'frontend/dist'),
        ('user_container/skills', 'user_container/skills'),
        ('user_container/templates', 'user_container/templates'),
    ] + tiktoken_datas,
    hiddenimports=[
        # uvicorn internals
        'uvicorn',
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.loops.asyncio',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.http.h11_impl',
        'uvicorn.protocols.http.httptools_impl',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.protocols.websockets.wsproto_impl',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'uvicorn.lifespan.off',
        # fastapi
        'fastapi',
        'fastapi.staticfiles',
        'fastapi.responses',
        'fastapi.middleware.cors',
        'starlette',
        'starlette.responses',
        'starlette.staticfiles',
        # app modules
        'user_container',
        'user_container.app',
        'user_container.config',
        'user_container.db.db',
        'user_container.agent.agent',
        'user_container.agent.llm_client',
        'user_container.agent.routing',
        'user_container.agent.prompts',
        'user_container.agent.skill_loader',
        'user_container.agent.skill_router',
        'user_container.agent.delegate_executor',
        'user_container.agent.explore_executor',
        'user_container.tools',
        'user_container.jobs.queue',
        'user_container.jobs.job',
        'user_container.scheduler.scheduler',
        'user_container.usage.tracker',
        # LLM providers
        'anthropic',
        'openai',
        'httpx',
        'httpx._transports',
        'httpx._transports.default',
        # data libs
        'pdfplumber',
        'openpyxl',
        'docx',
        'bs4',
        # tokens
        'tiktoken',
        'tiktoken_ext',
        'tiktoken_ext.openai_public',
        # scheduler
        'apscheduler',
        'apscheduler.schedulers.asyncio',
        'apscheduler.triggers.cron',
        'apscheduler.jobstores.memory',
        'croniter',
        # templates
        'jinja2',
        # observability
        'sentry_sdk',
        'sentry_sdk.integrations.fastapi',
        'sentry_sdk.integrations.starlette',
        'langfuse',
        # multipart
        'multipart',
        'python_multipart',
        # misc
        'rich',
        'sqlite3',
        'email',
        'email.mime',
    ] + pydantic_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'PIL',
        'scipy',
        'numpy.testing',
        'pytest',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='zeno',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='zeno',
)

app = BUNDLE(
    coll,
    name='ZENO.app',
    icon=None,
    bundle_identifier='com.zeno.app',
    info_plist={
        'CFBundleName': 'ZENO',
        'CFBundleDisplayName': 'ZENO',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHighResolutionCapable': True,
    },
)
