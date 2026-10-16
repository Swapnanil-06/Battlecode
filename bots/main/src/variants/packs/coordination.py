"""Six short-lived camp claims in the platform's eight shared bytes.

High 16 bits: last write round. Six low bytes: 6-bit job (0=none),
2-bit write round. Every writer prunes expired records before advancing the
full timestamp, preventing stale claims from reviving at modulo wrap.
"""


def live_claims(word, now):
    stamp = word >> 48
    elapsed = now - stamp
    if elapsed < 0 or elapsed > 2:
        return [0] * 6
    records = []
    for slot in range(6):
        record = (word >> (slot * 8)) & 255
        age = ((stamp - (record >> 6)) & 3) + elapsed
        records.append(record if record & 63 and age <= 2 else 0)
    return records


def publish(word, slot, job, now):
    if not 0 <= slot < 6 or not 0 <= job <= 63 or not 0 <= now <= 65535:
        raise ValueError('claim outside shared-memory encoding')
    records = live_claims(word, now)
    records[slot] = (((now & 3) << 6) | job) if job else 0
    return (now << 48) | sum(record << (index * 8)
                             for index, record in enumerate(records))


def claimed_jobs(word, slot, now):
    return {record & 63 for index, record in enumerate(live_claims(word, now))
            if index != slot and record & 63}


def job_claim_counts(word, slot, now):
    counts = {}
    for index, record in enumerate(live_claims(word, now)):
        if index != slot and record & 63:
            job = record & 63
            counts[job] = counts.get(job, 0) + 1
    return counts

