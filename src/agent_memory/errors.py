from __future__ import annotations


class AgentMemoryError(Exception):
    code = "AGENT_MEMORY_ERROR"
    exit_code = 1


class UsageError(AgentMemoryError):
    code = "USAGE_ERROR"
    exit_code = 2


class DatabaseError(AgentMemoryError):
    code = "DATABASE_ERROR"
    exit_code = 3


class MemoryNotFoundError(AgentMemoryError):
    code = "MEMORY_NOT_FOUND"
    exit_code = 4


class ValidationError(AgentMemoryError):
    code = "VALIDATION_ERROR"
    exit_code = 5


class FileOperationError(AgentMemoryError):
    code = "FILE_OPERATION_ERROR"
    exit_code = 6
