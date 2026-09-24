"""Generate CSVs matching Inside Airbnb's detailed listings/calendar/reviews schema."""
import csv, gzip, random, json, datetime as dt
random.seed(42)

LISTING_COLS = ["id","listing_url","scrape_id","last_scraped","source","name","description",
"neighborhood_overview","picture_url","host_id","host_url","host_name","host_since","host_location",
"host_about","host_response_time","host_response_rate","host_acceptance_rate","host_is_superhost",
"host_thumbnail_url","host_picture_url","host_neighbourhood","host_listings_count",
"host_total_listings_count","host_verifications","host_has_profile_pic","host_identity_verified",
"neighbourhood","neighbourhood_cleansed","neighbourhood_group_cleansed","latitude","longitude",
"property_type","room_type","accommodates","bathrooms","bathrooms_text","bedrooms","beds","amenities",
"price","minimum_nights","maximum_nights","minimum_minimum_nights","maximum_minimum_nights",
"minimum_maximum_nights","maximum_maximum_nights","minimum_nights_avg_ntm","maximum_nights_avg_ntm",
"calendar_updated","has_availability","availability_30","availability_60","availability_90",
"availability_365","calendar_last_scraped","number_of_reviews","number_of_reviews_ltm",
"number_of_reviews_l30d","first_review","last_review","review_scores_rating","review_scores_accuracy",
"review_scores_cleanliness","review_scores_checkin","review_scores_communication",
"review_scores_location","review_scores_value","license","instant_bookable",
"calculated_host_listings_count","calculated_host_listings_count_entire_homes",
"calculated_host_listings_count_private_rooms","calculated_host_listings_count_shared_rooms",
"reviews_per_month"]

NBHD = {"london":["Westminster","Camden","Hackney","Tower Hamlets","Southwark","Islington","Lambeth","Kensington and Chelsea"],
        "edinburgh":["Old Town","New Town","Leith","Marchmont","Stockbridge"],
        "manchester":["City Centre","Northern Quarter","Salford","Didsbury"]}
CENTRE = {"london":(51.5074,-0.1278),"edinburgh":(55.9533,-3.1883),"manchester":(53.4794,-2.2453)}
ROOMS = ["Entire home/apt","Private room","Shared room","Hotel room"]
PROPS = ["Entire rental unit","Private room in home","Entire condo","Entire home","Shared room in hostel"]
AMEN = ["Wifi","Fast wifi – 200 Mbps","Air conditioning","Free parking on premises","Washer",
        "Dishwasher","Hot tub","Pool","Self check-in","Dedicated workspace","Pets allowed",
        "Elevator","Kitchen","Heating","TV","Hair dryer","Iron","Smoke alarm"]
BATHTXT = ["1 bath","1.5 baths","2 baths","1 shared bath","Half-bath","1 private bath","","2.5 baths"]

def make_city(city, n_listings, n_hosts, outdir):
    hosts = [(1000000+i, f"2015-0{random.randint(1,9)}-1{random.randint(0,9)}") for i in range(n_hosts)]
    lat0, lon0 = CENTRE[city]
    rows, ids = [], []
    for i in range(n_listings):
        lid = int(f"{abs(hash(city))%90+10}{i:07d}")
        ids.append(lid)
        hid, hsince = random.choice(hosts)
        room = random.choices(ROOMS, weights=[60,30,5,5])[0]
        acc = random.randint(1,10)
        base = 40 + acc*22 + (60 if room=="Entire home/apt" else 0) + random.gauss(0,25)
        price = max(8, base)
        # 1% junk prices, like the real data
        if random.random() < 0.01: price = random.choice([0, 9999, 25000])
        n_rev = random.choices([0, random.randint(1,20), random.randint(20,300)], weights=[25,40,35])[0]
        has_rev = n_rev > 0
        r = dict.fromkeys(LISTING_COLS, "")
        r.update({
          "id": lid, "listing_url": f"https://airbnb.com/rooms/{lid}", "scrape_id":"20260612000000",
          "last_scraped":"2026-06-12", "name": f'Lovely "flat", {city}', "description":"Nice place.\nWith newline.",
          "host_id": hid, "host_name":"Alex", "host_since": hsince,
          "host_response_rate": random.choice(["100%","90%",""]),
          "host_acceptance_rate": random.choice(["95%","80%",""]),
          "host_is_superhost": random.choice(["t","f",""]),
          "host_listings_count": str(random.randint(1,40)),
          "host_identity_verified": random.choice(["t","f"]),
          "neighbourhood_cleansed": random.choice(NBHD[city]),
          "latitude": round(lat0+random.gauss(0,0.05),6), "longitude": round(lon0+random.gauss(0,0.07),6),
          "property_type": random.choice(PROPS), "room_type": room,
          "accommodates": acc,
          "bathrooms": "",                      # genuinely empty in real snapshots
          "bathrooms_text": random.choice(BATHTXT),
          "bedrooms": random.choice(["1","2","3","","4"]),
          "beds": random.choice(["1","2","3",""]),
          "amenities": json.dumps(random.sample(AMEN, random.randint(3,12))),
          "price": f"${price:,.2f}" if random.random()>0.05 else "",
          "minimum_nights": random.choices([1,2,3,30,90],weights=[40,30,20,8,2])[0],
          "maximum_nights": random.choice([365,1125,30]),
          "availability_30": random.randint(0,30), "availability_60": random.randint(0,60),
          "availability_90": random.randint(0,90), "availability_365": random.randint(0,365),
          "number_of_reviews": n_rev, "number_of_reviews_ltm": min(n_rev, random.randint(0,40)),
          "first_review": "2019-04-11" if has_rev else "",
          "last_review": "2026-05-30" if has_rev else "",
          "review_scores_rating": f"{random.uniform(3.5,5):.2f}" if has_rev else "",
          "review_scores_cleanliness": f"{random.uniform(3.5,5):.2f}" if has_rev else "",
          "review_scores_location": f"{random.uniform(3.5,5):.2f}" if has_rev else "",
          "review_scores_value": f"{random.uniform(3.5,5):.2f}" if has_rev else "",
          "instant_bookable": random.choice(["t","f"]),
          "reviews_per_month": f"{random.uniform(0.1,6):.2f}" if has_rev else "",
        })
        rows.append(r)
    with gzip.open(f"{outdir}/{city}_listings.csv.gz","wt",newline="",encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=LISTING_COLS); w.writeheader(); w.writerows(rows)

    # calendar: 90 nights per listing to keep the test quick
    start = dt.date(2026,6,12)
    with gzip.open(f"{outdir}/{city}_calendar.csv.gz","wt",newline="",encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["listing_id","date","available","minimum_nights","maximum_nights"])
        for lid in ids:
            b = random.uniform(45,260)
            for d in range(90):
                day = start+dt.timedelta(days=d)
                wknd = day.weekday() in (4,5)
                p = b*(1.25 if wknd else 1.0)
                w.writerow([lid, day.isoformat(), random.choice(["t","f"]), 1, 365])

    with gzip.open(f"{outdir}/{city}_reviews.csv.gz","wt",newline="",encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["listing_id","id","date","reviewer_id","reviewer_name","comments"])
        rid = abs(hash(city)) % 1000 * 100000
        for lid in ids:
            for _ in range(random.randint(0,8)):
                rid += 1
                w.writerow([lid, rid, f"2025-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
                            random.randint(1,999999), "Sam", 'Great stay!\nWould "return".'])
    print(f"{city}: {n_listings} listings, {n_listings*90} calendar rows")

if __name__ == "__main__":
    out = "data/raw"
    make_city("london", 4000, 900, out)
    make_city("edinburgh", 1200, 400, out)
    make_city("manchester", 800, 300, out)
