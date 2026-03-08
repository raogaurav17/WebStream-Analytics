#!/usr/bin/env python3
"""
E-Commerce Event Producer — Realistic synthetic event stream.

Behavioral realism features:
  - User personas  : browsers, impulse buyers, researchers, loyalists
  - Product tiers  : viral / popular / niche, each with distinct view→buy funnels
  - Traffic spikes : flash sales, lunch-hour rush, evening peak
  - Session flow   : users follow realistic view→click→cart→purchase journeys
  - Price anchoring: high-value items get more views but fewer purchases
"""

from kafka import KafkaProducer
from kafka.errors import KafkaError
import time
import json
import random
import uuid
from datetime import datetime, timezone
import argparse
import os
import sys
import math

# ---------------------------------------------------------------------------
# Product catalogue
# ---------------------------------------------------------------------------

CATEGORIES = ["electronics", "clothing", "furniture", "food", "books", "sports"]

PRICE_RANGES = {
    "electronics": (50.0,   1500.0),
    "clothing":    (15.0,    200.0),
    "furniture":  (100.0,   2500.0),
    "food":         (5.0,     50.0),
    "books":        (8.0,     35.0),
    "sports":      (20.0,    500.0),
}

# Each product has a tier that controls its popularity and conversion rate.
# tier: "viral" | "popular" | "niche"
PRODUCTS: list[dict] = []
for pid in range(1, 501):
    cat = random.choice(CATEGORIES)
    roll = random.random()
    if roll < 0.05:          # 5 % viral
        tier = "viral"
    elif roll < 0.25:        # 20 % popular
        tier = "popular"
    else:                    # 75 % niche
        tier = "niche"
    lo, hi = PRICE_RANGES[cat]
    PRODUCTS.append({
        "product_id": f"p_{pid}",
        "category":   cat,
        "tier":       tier,
        "price":      round(random.uniform(lo, hi), 2),
    })

# Index products for weighted sampling
_TIER_WEIGHTS = {"viral": 12, "popular": 4, "niche": 1}
_PRODUCT_WEIGHTS = [_TIER_WEIGHTS[p["tier"]] for p in PRODUCTS]

def pick_product() -> dict:
    return random.choices(PRODUCTS, weights=_PRODUCT_WEIGHTS, k=1)[0]

# ---------------------------------------------------------------------------
# User personas
# ---------------------------------------------------------------------------

class UserPersona:
    """Encapsulates a user's behavioural profile."""

    TYPES = ["browser", "impulse_buyer", "researcher", "loyalist"]

    # Conditional drop-off at each funnel step (given previous step happened).
    # Tuple = (view->click, click->cart, cart->purchase)
    # Net CVR = product of all three:
    #   browser:       0.12 * 0.20 * 0.08  = ~0.2%
    #   impulse_buyer: 0.35 * 0.50 * 0.25  = ~4.4%
    #   researcher:    0.30 * 0.35 * 0.18  = ~1.9%
    #   loyalist:      0.40 * 0.55 * 0.30  = ~6.6%
    # Blended ~3.3% across equal persona mix -- in line with industry average
    STEP_PROBS = {
        "browser":       (0.12, 0.20, 0.08),
        "impulse_buyer": (0.35, 0.50, 0.25),
        "researcher":    (0.30, 0.35, 0.18),
        "loyalist":      (0.40, 0.55, 0.30),
    }

    # Average seconds between two events for this persona
    THINK_TIME = {
        "browser":       0.8,
        "impulse_buyer": 0.3,
        "researcher":    1.2,
        "loyalist":      0.5,
    }

    def __init__(self, user_id: str):
        self.user_id    = user_id
        self.ptype      = random.choice(self.TYPES)
        self.fw         = self.STEP_PROBS[self.ptype]
        self.think_time = self.THINK_TIME[self.ptype]

    def run_session(self) -> list[dict]:
        """
        Simulate one complete shopping session for this user.
        Always starts with a view, then each subsequent step is rolled
        against STEP_PROBS. Returns the list of events emitted (1-4 events).
        """
        stage_names = ["view", "click", "add_to_cart", "purchase"]
        product = pick_product()

        tier_boost    = {"viral": 1.4, "popular": 1.0, "niche": 0.65}[product["tier"]]
        price_penalty = max(0.4, 1.0 - product["price"] / 3000.0)

        events = []
        for stage in range(4):
            events.append(self._build_event(stage_names[stage], product))
            if stage < 3:
                prob = self.fw[stage] * tier_boost * price_penalty
                if random.random() >= prob:
                    break   # user drops off here

        return events

    def _build_event(self, event_type: str, product: dict = None) -> dict:
        p   = product or self.session_product
        ip  = f"192.168.{random.randint(1,255)}.{random.randint(1,255)}"
        return {
            "event_id":    str(uuid.uuid4()),
            "event_type":  event_type,
            "user_id":     self.user_id,
            "persona":     self.ptype,
            "product_id":  p["product_id"],
            "category":    p["category"],
            "product_tier": p["tier"],
            "price":       p["price"],
            "timestamp":   datetime.now(timezone.utc).isoformat(),
            "ip_address":  ip,
        }


# ---------------------------------------------------------------------------
# Traffic-spike model
# ---------------------------------------------------------------------------

class TrafficModel:
    """
    Returns a multiplier (≥ 1.0) for the current moment based on:
      - Time-of-day curve  (lunch & evening peaks)
      - Scheduled flash-sale spikes
      - Random viral bursts
    """

    def __init__(self, base_rate: int):
        self.base_rate = base_rate
        self._next_burst_at   = time.time() + random.uniform(30, 120)
        self._burst_intensity = 1.0
        self._burst_duration  = 0.0
        self._burst_start     = 0.0

    def multiplier(self) -> float:
        now = time.time()
        m   = self._time_of_day_multiplier()
        m  *= self._flash_sale_multiplier(now)
        m  *= self._viral_burst_multiplier(now)
        return max(0.1, m)

    # -- helpers -------------------------------------------------------------

    def _time_of_day_multiplier(self) -> float:
        """Smooth sinusoidal curve peaking at noon and 8 pm (simulated fast)."""
        # We compress one "day" into ~120 seconds for demo visibility
        t   = (time.time() % 120) / 120          # [0,1) within fake day
        hr  = t * 24                             # fake hour
        # Two peaks: noon (12) and evening (20)
        lunch   = math.exp(-0.5 * ((hr - 12) / 2) ** 2)
        evening = math.exp(-0.5 * ((hr - 20) / 2) ** 2)
        base    = 0.3
        return base + 0.5 * lunch + 0.7 * evening

    def _flash_sale_multiplier(self, now: float) -> float:
        """Scheduled flash sales every ~90 s, last 10 s, 4× spike."""
        cycle = now % 90
        if cycle < 10:
            ramp = math.sin(math.pi * cycle / 10)
            return 1.0 + 3.0 * ramp
        return 1.0

    def _viral_burst_multiplier(self, now: float) -> float:
        """Random viral bursts: 2–5× for 5–15 s, every 30–120 s."""
        if now >= self._next_burst_at:
            self._burst_intensity = random.uniform(2.0, 5.0)
            self._burst_duration  = random.uniform(5.0, 15.0)
            self._burst_start     = now
            self._next_burst_at   = now + random.uniform(30, 120)

        elapsed = now - self._burst_start
        if elapsed < self._burst_duration:
            fade = 1.0 - elapsed / self._burst_duration
            return 1.0 + (self._burst_intensity - 1.0) * fade
        return 1.0

    def effective_rate(self) -> float:
        return self.base_rate * self.multiplier()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Realistic E-Commerce Event Producer")
    parser.add_argument("--broker", default=None,
                        help="Kafka broker (auto-detected in Docker)")
    parser.add_argument("--rate",  type=int, default=500,
                        help="Base events per second (spikes multiply this)")
    parser.add_argument("--users", type=int, default=200,
                        help="Pool of simulated users")
    args = parser.parse_args()

    if args.broker is None:
        in_docker  = os.path.exists("/.dockerenv")
        args.broker = "kafka:29092" if in_docker else "localhost:9092"

    try:
        producer = KafkaProducer(
            bootstrap_servers=args.broker,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            acks="all",
            retries=5,
            max_in_flight_requests_per_connection=1,
        )
    except Exception as e:
        print(f"❌  Failed to connect to Kafka at {args.broker}")
        print(f"    Error: {e}")
        sys.exit(1)

    # Initialise user personas
    personas: dict[str, UserPersona] = {
        f"u_{i}": UserPersona(f"u_{i}") for i in range(1, args.users + 1)
    }
    user_ids = list(personas.keys())

    traffic = TrafficModel(args.rate)

    print("─" * 55)
    print("  🛒  Realistic E-Commerce Event Producer")
    print("─" * 55)
    print(f"  Broker    : {args.broker}")
    print(f"  Base rate : {args.rate} events/s  (spikes apply)")
    print(f"  Users     : {args.users}  ({len([p for p in personas.values() if p.ptype=='impulse_buyer'])} impulse buyers, "
          f"{len([p for p in personas.values() if p.ptype=='browser'])} browsers, …)")
    print(f"  Products  : {len(PRODUCTS)}  "
          f"({sum(1 for p in PRODUCTS if p['tier']=='viral')} viral, "
          f"{sum(1 for p in PRODUCTS if p['tier']=='popular')} popular, "
          f"{sum(1 for p in PRODUCTS if p['tier']=='niche')} niche)")
    print("─" * 55)
    print()

    event_count  = 0
    error_count  = 0
    stats: dict[str, int] = {k: 0 for k in ["view","click","add_to_cart","purchase"]}

    try:
        while True:
            rate = traffic.effective_rate()
            interval = 1.0 / max(rate, 0.1)

            user_id = random.choice(user_ids)
            persona = personas[user_id]

            # Run a complete session for this user: view → (click → cart → purchase)?
            # Each step has a think-time delay so events feel spread out in time.
            session_events = persona.run_session()

            for event in session_events:
                future = producer.send("events", event)
                try:
                    future.get(timeout=5)
                    event_count               += 1
                    stats[event["event_type"]] += 1
                except KafkaError as e:
                    error_count += 1
                    if error_count % 10 == 1:
                        print(f"⚠️   Kafka send error: {str(e)[:80]}")

            # Progress summary every 200 events
            if event_count % 200 == 0 and event_count > 0:
                mult = traffic.multiplier()
                spike_tag = ""
                if mult > 3.5:
                    spike_tag = "  🚀 VIRAL BURST"
                elif mult > 2.0:
                    spike_tag = "  ⚡ FLASH SALE"
                elif mult > 1.3:
                    spike_tag = "  📈 peak hour"

                conv_rate = (stats["purchase"] / max(stats["view"], 1)) * 100
                print(
                    f"  ✓ {event_count:>6} sent  |  "
                    f"×{mult:.1f} rate={rate:.1f}/s  |  "
                    f"view={stats['view']}  click={stats['click']}  "
                    f"cart={stats['add_to_cart']}  buy={stats['purchase']}  "
                    f"CVR={conv_rate:.1f}%"
                    f"{spike_tag}"
                )

            time.sleep(interval)

    except KeyboardInterrupt:
        print(f"\n{'─'*55}")
        print(f"  Producer stopped after {event_count} events")
        print(f"  Final funnel  —  "
              f"view:{stats['view']}  click:{stats['click']}  "
              f"cart:{stats['add_to_cart']}  purchase:{stats['purchase']}")
        if stats["view"]:
            print(f"  Overall CVR: {stats['purchase']/stats['view']*100:.2f}%")
        producer.flush(timeout=10)
        producer.close()


if __name__ == "__main__":
    main()