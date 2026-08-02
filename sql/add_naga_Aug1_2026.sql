
INSERT INTO properties (
    name,
    platform,
    listing_url,
    municipality,
    province,
    maximum_guests,
    active
)
VALUES
(
    'Spacious Home for Big Families in Naga City by AGN',
    'airbnb',
    'https://www.airbnb.com/rooms/1236851470687690176',
    'Naga City',
    'Camarines Sur',
    1,
    12,
    TRUE
),
(
    'Casa Ayá - Naga City Staycation',
    'airbnb',
    'https://www.airbnb.com/rooms/954177044074914025',
    'Naga City',
    'Camarines Sur',
    1,
    NULL,
    TRUE
),
(
    'Blue Paseo Grande Inn - Double Room',
    'airbnb',
    'https://www.airbnb.com/rooms/15523344',
    'Naga City',
    'Camarines Sur',
    1,
    NULL,
    TRUE
),
(
    '2BR 1CR Fast WiFi Netflix Parking Kitchen',
    'airbnb',
    'https://www.airbnb.com/rooms/16891904',
    'Naga City',
    'Camarines Sur',
    1,
    5,
    TRUE
),
(
    'Temporary House in Pili Camarines Sur',
    'airbnb',
    'https://www.airbnb.com/rooms/1243122121936555950',
    'Pili',
    'Camarines Sur',
    1,
    NULL,
    TRUE
),
(
    'FERN Serenity Space',
    'airbnb',
    'https://www.airbnb.com/rooms/41270698',
    'Pili',
    'Camarines Sur',
    1,
    NULL,
    TRUE
),
(
    'Transient House in Camarines Sur',
    'airbnb',
    'https://www.airbnb.com/rooms/1101845881403165284',
    'Pili',
    'Camarines Sur',
    1,
    10,
    TRUE
),
(
    'Spacious Transient House with Wi-Fi and Parking',
    'airbnb',
    'https://www.airbnb.com/rooms/851034518362961140',
    'Pili',
    'Camarines Sur',
    1,
    20,
    TRUE
),
(
    '3BR Transient House in Camella Homes Pili',
    'airbnb',
    'https://www.airbnb.com/rooms/1638083425374742841',
    'Pili',
    'Camarines Sur',
    1,
    7,
    TRUE
),
(
    'Apartment in Cadlan Near CWC',
    'airbnb',
    'https://www.airbnb.com/rooms/24089040',
    'Pili',
    'Camarines Sur',
    1,
    2,
    TRUE
),
(
    'Winch House - Haven Near Watersports and Golf',
    'airbnb',
    'https://www.airbnb.com/rooms/53619884',
    'Pili',
    'Camarines Sur',
    1,
    12,
    TRUE
),
(
    'Provincial Feels at Casa Camia',
    'airbnb',
    'https://www.airbnb.com/rooms/831833219412292752',
    'Iriga City',
    'Camarines Sur',
    1,
    NULL,
    TRUE
),
(
    'Centro Goa Fully Furnished with Netflix',
    'airbnb',
    'https://www.airbnb.com/rooms/31815589',
    'Goa',
    'Camarines Sur',
    1,
    NULL,
    TRUE
),
(
    'CHL Transient House 2',
    'airbnb',
    'https://www.airbnb.com/rooms/1368528806963303566',
    'San Felipe',
    'Camarines Sur',
    1,
    10,
    TRUE
)

/*
ON CONFLICT (listing_url) DO UPDATE
SET
    name = EXCLUDED.name,
    municipality = EXCLUDED.municipality,
    province = EXCLUDED.province,
    maximum_guests = EXCLUDED.maximum_guests,
    active = TRUE,
    updated_at = NOW();
*/