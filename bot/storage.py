import json
import os

from .config import (
    AWAL_CHAT_IDS,
    BOT_STATE_FILE,
    CATATAN_FILE,
    CHAT_IDS_FILE,
    FILTER_STATE_FILE,
    PINNED_STATE_FILE,
    WILAYAH_STATE_FILE,
)


# ==================== UMUM ====================
def _load_json(path, default):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return default


def _save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f)


# ==================== GRUP TERDAFTAR ====================
def load_chat_ids():
    env_ids = os.getenv("CHAT_IDS", "")
    env_list = [cid.strip() for cid in env_ids.split(",") if cid.strip()] if env_ids else []

    file_ids = _load_json(CHAT_IDS_FILE, [])

    merged = list(dict.fromkeys(env_list + file_ids + AWAL_CHAT_IDS))
    if merged != file_ids:
        _save_json(CHAT_IDS_FILE, merged)
    return merged


def save_chat_ids(ids):
    _save_json(CHAT_IDS_FILE, ids)


def tambah_chat_id(chat_id):
    chat_id = str(chat_id)
    ids = load_chat_ids()
    if chat_id not in ids:
        ids.append(chat_id)
        save_chat_ids(ids)
        print(f"[GRUP] Grup baru terdaftar: {chat_id}")
        return True
    return False


def hapus_chat_id(chat_id):
    chat_id = str(chat_id)
    ids = load_chat_ids()
    if chat_id in ids:
        ids.remove(chat_id)
        save_chat_ids(ids)
        print(f"[GRUP] Grup dihapus: {chat_id}")
        return True
    return False


# ==================== STATUS ON/OFF BOT ====================
def load_bot_state():
    return {str(k): bool(v) for k, v in _load_json(BOT_STATE_FILE, {}).items()}


def save_bot_state(state):
    _save_json(BOT_STATE_FILE, state)


def is_bot_aktif(chat_id):
    return load_bot_state().get(str(chat_id), True)


def set_bot_aktif(chat_id, aktif):
    state = load_bot_state()
    state[str(chat_id)] = bool(aktif)
    save_bot_state(state)
    print(f"[STATUS] Grup {chat_id} -> {'AKTIF' if aktif else 'NONAKTIF'}")


def toggle_bot(chat_id):
    baru = not is_bot_aktif(chat_id)
    set_bot_aktif(chat_id, baru)
    return baru


# ==================== CATATAN TIKET TERKIRIM ====================
def load_sent_tickets():
    return set(_load_json(CATATAN_FILE, []))


def save_sent_tickets(sent_set):
    _save_json(CATATAN_FILE, list(sent_set))


# ==================== PILIHAN WILAYAH PER GRUP ====================
def load_wilayah_state():
    return {str(k): str(v) for k, v in _load_json(WILAYAH_STATE_FILE, {}).items()}


def save_wilayah_state(state):
    _save_json(WILAYAH_STATE_FILE, state)


def get_wilayah(chat_id):
    return load_wilayah_state().get(str(chat_id))


def set_wilayah(chat_id, wilayah):
    state = load_wilayah_state()
    state[str(chat_id)] = wilayah
    save_wilayah_state(state)
    print(f"[WILAYAH] Grup {chat_id} -> {wilayah}")


# ==================== STATUS FILTER WILAYAH ====================
def load_filter_state():
    return {str(k): bool(v) for k, v in _load_json(FILTER_STATE_FILE, {}).items()}


def save_filter_state(state):
    _save_json(FILTER_STATE_FILE, state)


def is_filter_aktif(chat_id):
    return load_filter_state().get(str(chat_id), False)


def set_filter(chat_id, aktif):
    state = load_filter_state()
    state[str(chat_id)] = bool(aktif)
    save_filter_state(state)
    print(f"[FILTER] Grup {chat_id} filter-> {'ON' if aktif else 'OFF'}")


# ==================== PESAN MENU YANG DI-PIN ====================
def load_pinned_state():
    return {str(k): int(v) for k, v in _load_json(PINNED_STATE_FILE, {}).items()}


def save_pinned_state(state):
    _save_json(PINNED_STATE_FILE, state)


def get_pinned(chat_id):
    return load_pinned_state().get(str(chat_id))


def set_pinned(chat_id, msg_id):
    state = load_pinned_state()
    state[str(chat_id)] = int(msg_id)
    save_pinned_state(state)