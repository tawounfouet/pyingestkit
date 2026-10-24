"""Stable process exit codes for the PyIngestKit CLI."""

from __future__ import annotations

from enum import IntEnum


class ExitCode(IntEnum):
    """Process exit codes defined by the CLI v1 candidate contract."""

    SUCCESS = 0  # Exécution nominale
    GENERAL_ERROR = 1  # Erreur d'arguments ou de syntaxe utilisateur
    VALIDATION_ERROR = 2  # Échec de validation statique (configuration, job, schéma)
    EXECUTION_FAILURE = 3  # Échec d'exécution du job d'ingestion
    SECURITY_ERROR = 4  # Violation de sécurité (path traversal, fuite de secret)
    MISSING_OPTIONAL_DEPENDENCY = (
        11  # Extra ou dépendance optionnelle manquante (cli, postgres, s3)
    )
    FILESYSTEM_ERROR = 12  # Fichier introuvable ou permissions insuffisantes
    INTERNAL_ERROR = 70  # Exception non interceptée (bug runtime interne)
    INTERRUPTED = 130  # Interruption utilisateur SIGINT (Ctrl+C)
    BROKEN_PIPE = 141  # Tube brisé SIGPIPE (Unix Broken Pipe)


__all__ = ["ExitCode"]
