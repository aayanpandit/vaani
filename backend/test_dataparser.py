import dateparser

tests = [
    "tomorrow 5 PM",
    "Friday 2 PM",
    "15 July 11 AM",
    "next Monday 6 PM",
]

for text in tests:
    dt = dateparser.parse(
        text,
        settings={
            "TIMEZONE": "Asia/Kolkata",
            "RETURN_AS_TIMEZONE_AWARE": False,
        },
    )

    print(f"{text} -> {dt}")