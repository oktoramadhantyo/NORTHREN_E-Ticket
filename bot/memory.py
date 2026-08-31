"""State in-memory yang sifatnya sementara (hasil siklus terakhir)."""

SIMPANAN_TIKET = {}


def update_snapshot(snapshot):
    global SIMPANAN_TIKET
    SIMPANAN_TIKET.clear()
    SIMPANAN_TIKET.update(snapshot)