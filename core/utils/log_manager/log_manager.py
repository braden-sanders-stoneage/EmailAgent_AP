import os
import datetime
import traceback


_current_log_file = None


def _ensure_log_directory():
    log_dir = "core/utils/log_manager/log_files"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    return log_dir


def _initialize_log_file():
    global _current_log_file
    if _current_log_file is None:
        log_dir = _ensure_log_directory()
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        _current_log_file = os.path.join(log_dir, f"execution_{timestamp}.log")
    return _current_log_file


def _write_log(message):
    log_file = _initialize_log_file()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}\n"
    
    print(f"[{timestamp}] {message}")
    
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(log_entry)


def _write_error_log(message):
    log_file = _initialize_log_file()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}\n"
    
    print(f"❌ [{timestamp}] ERROR: {message}")
    
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(log_entry)


def log_error(context, exception):
    exception_type = type(exception).__name__
    exception_message = str(exception)
    stack_trace = ''.join(traceback.format_exception(type(exception), exception, exception.__traceback__))
    
    print('!'*50)
    print('\n\n\n')

    _write_error_log(f"{context}")
    _write_error_log(f"  Exception Type: {exception_type}")
    _write_error_log(f"  Exception Message: {exception_message}")
    _write_error_log(f"  Stack Trace:")
    
    for line in stack_trace.strip().split('\n'):
        _write_error_log(f"    {line}")

    print('\n\n\n')
    print('!'*50)


def log_attachments_process_start(total_count: int):
    _write_log(f"ATTACHMENTS: Processing {total_count} attachment(s)")


def log_attachments_completed(images: int, msgs: int, skipped: int):
    _write_log(f"ATTACHMENTS: Completed. images={images} msgs={msgs} skipped={skipped}")


