from collector import collect_signals

signals = collect_signals(max_videos=3)

print(f"Found {len(signals)} signals")

for signal in signals:
    print(signal)
    print("-" * 80)