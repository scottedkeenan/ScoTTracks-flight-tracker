CREATE TABLE `scottedk_ogn_logs`.`airfields` ( `id` SMALLINT UNSIGNED NOT NULL AUTO_INCREMENT , `name` VARCHAR(255) NOT NULL , `nice_name` VARCHAR(255) NOT NULL , `latitude` DOUBLE NOT NULL , `longitude` DOUBLE NOT NULL , `elevation` FLOAT NOT NULL , PRIMARY KEY (`id`));

INSERT INTO `scottedk_ogn_logs`.`airfields`(`name`, `nice_name`, `latitude`, `longitude`, `elevation`)
VALUES
('andreas', 'Andreas Gliding Club', 54.373160000000000, -4.429180000000000, 32),
('anglia', 'Anglia', 52.122800000000000, 0.967760000000000, 90),
('wyvern', 'Wyvern', 51.291010000000000, -1.779130000000000, 176),
('banbury', 'Banbury Gliding Club', 52.032070000000000, -1.211410000000000, 157),
('bannerdown', 'Bannerdown Gliding Club', 51.303923300000000, -2.121927700000000, 69),
('bath_wilts_north_dorset', 'Bath, Wilts & North Dorset Gliding Club', 51.130639000000000, -2.226282000000000, 137),
('bidford_gliding_flying_club', 'Bidford Gliding & Flying Club', 52.141130000000000, -1.845330000000000, 43),
('black_mountains', 'Black Mountains Gliding Club', 51.979140000000000, -3.203440000000000, 297),
('bognor_regis', 'Bognor Regis Gliding Club', 50.802560000000000, -0.664710000000000, 2),
('booker', 'Booker Gliding Club', 51.610170000000000, -0.801070000000000, 151),
('borders', 'Borders Gliding Club', 55.589410000000000, -2.084430000000000, 44),
('bowland_forest', 'Bowland Forest Gliding Club', 53.886160000000000, -2.619980000000000, 185),
('bristol_gloucestershire', 'Bristol & Gloucestershire Gliding Club', 51.715200000000000, -2.283020000000000, 213),
('buckminster', 'Buckminster Gliding Club', 52.830200000000000, -0.700290000000000, 142),
('burn', 'Burn Gliding Club', 53.749560000000000, -1.097070000000000, 7),
('cairngorm', 'Cairngorm Gliding Club', 57.106020000000000, -3.887130000000000, 269),
('cambridge', 'Cambridge Gliding Club', 52.166060000000000, -0.117360000000000, 78),
('channel', 'Channel Gliding Club', 51.179270000000000, 1.280050000000000, 97),
('chilterns', 'Chilterns Gliding Club', 51.786290000000000, -0.736240000000000, 115),
('cotswold', 'Cotswold Gliding Club', 51.712180000000000, -2.126120000000000, 181),
('cranwell', 'Cranwell Gliding Club', 53.040790000000000, -0.502460000000000, 69),
('darlton', 'Darlton Gliding Club', 53.247760000000000, -0.851560000000000, 37),
('dartmoor', 'Dartmoor Gliding Society', 50.591550000000000, -4.152370000000000, 233),
('deeside', 'Deeside Gliding Club', 57.075680000000000, -2.845040000000000, 144),
('denbigh', 'Denbigh Gliding', 53.208260000000000, -3.394290000000000, 42),
('derbyshire_lancashire', 'Derbyshire & Lancashire Gliding Club', 53.303540000000000, -1.728040000000000, 381),
('devon_somerset', 'Devon & Somerset Gliding Club', 50.852860000000000, -3.267340000000000, 265),
('dorset', 'Dorset Gliding Club', 50.712400000000000, -2.217560000000000, 67),
('dumfries_district', 'Dumfries & District Gliding Club', 54.943110000000000, -3.740900000000000, 188),
('east_sussex', 'East Sussex Gliding Club', 50.909140000000000, 0.105530000000000, 34),
('edensoaring', 'Edensoaring', 54.693450000000000, -2.579180000000000, 183),
('essex_suffolk', 'Essex & Suffolk Gliding Club', 51.944070000000000, 0.802920000000000, 63),
('essex', 'Essex Gliding Club', 52.049530000000000, 0.557680000000000, 83),
('fenlands', 'Fenlands Gliding Club', 52.652410000000000, 0.545090000000000, 30),
('fulmar', 'Fulmar Gliding Club', 57.586433000000000, -3.321219000000000, 101),
('gliding_centre', 'Gliding Centre', 52.437180000000000, -1.051760000000000, 155),
('herefordshire', 'Herefordshire Gliding Club', 52.243440000000000, -2.883810000000000, 98),
('heron', 'Heron Gliding Club', 51.013580000000000, -2.647800000000000, 17),
('highland', 'Highland Gliding Club', 57.587019000000000, -3.303769000000000, 101),
('kent', 'Kent Gliding Club', 51.209460000000000, 0.831030000000000, 183),
('kestrel', 'Kestrel Gliding Club', 51.240460000000000, -0.945210000000000, 116),
('lakes', 'Lakes Gliding Club', 54.125180000000000, -3.260310000000000, 15),
('lasham_gliding_society', 'Lasham Gliding Society', 51.190240000000000, -1.032600000000000, 179),
('lincolnshire', 'Lincolnshire Gliding Club', 53.303420000000000, 0.168140000000000, 14),
('london', 'London Gliding Club', 51.873090000000000, -0.549520000000000, 133),
('mendip', 'Mendip Gliding Club', 51.259900000000000, -2.729140000000000, 258),
('midland', 'Midland Gliding Club', 52.518600000000000, -2.880800000000000, 427),
('motorglide', 'MotorGlide', 51.606980000000000, -1.669490000000000, 108),
('nene_valley', 'Nene Valley Gliding Club', 52.432150000000000, -0.147220000000000, 25),
('norfolk', 'Norfolk Gliding Club', 52.457210000000000, 1.161240000000000, 55),
('north_devon', 'North Devon Gliding Club', 50.927880000000000, -3.984820000000000, 196),
('north_wales', 'North Wales Gliding Club', 53.046570000000000, -3.219090000000000, 329),
('northumbria', 'Northumbria Gliding Club', 54.934370000000000, -1.839190000000000, 221),
('oxford', 'Oxford Gliding Club', 51.881020000000000, -1.227850000000000, 85),
('oxfordshire_sportflying', 'Oxfordshire Sportflying Gliding Club', 51.931610000000000, -1.441810000000000, 176),
('peterborough_spalding', 'Peterborough & Spalding Gliding Club', 52.711510000000000, -0.133860000000000, 2),
('portsmouth_naval', 'Portsmouth Naval', 51.145218000000000, -1.573062000000000, 85),
('raf_shawbury', 'RAF Shawbury Gliding Club', 52.8000000, -2.6700000, 76),
('rattlesden', 'Rattlesden Gliding Club', 52.169590000000000, 0.875090000000000, 85),
('sackville_vintage', 'Sackville Vintage Gliding Club', 52.262100000000000, -0.477640000000000, 67),
('scottish_gliding_centre', 'Scottish Gliding Centre', 56.189040000000000, -3.321830000000000, 109),
('seahawk', 'Seahawk Gliding Club', 50.081760000000000, -5.257840000000000, 69),
('shalbourne_gliding', 'Shalbourne Gliding', 51.337250000000000, -1.544520000000000, 188),
('shenington', 'Shenington Gliding Club', 52.080170000000000, -1.473450000000000, 185),
('shropshire_soaring', 'Shropshire Soaring', 52.833910000000000, -2.767630000000000, 83),
('south_wales', 'South Wales Gliding Club', 51.717920000000000, -2.843260000000000, 25),
('southdown', 'Southdown Gliding Club', 50.921870000000000, -0.473980000000000, 30),
('staffordshire', 'Staffordshire Gliding Club', 52.827770000000000, -2.209000000000000, 97),
('stratford_on_avon', 'Stratford On Avon Gliding Club', 52.235680000000000, -1.710590000000000, 115),
('suffolk_soaring_club', 'Suffolk Soaring Club', 52.347426000000000, 0.980218000000000, 27),
('surrey_hills', 'Surrey Hills Gliding Club', 51.301240000000000, -0.093770000000000, 172),
('trent_valley', 'Trent Valley Gliding Club', 53.459530000000000, -0.582660000000000, 60),
('ulster', 'Ulster Gliding Club', 55.137890000000000, -6.964890000000000, 3),
('vale_of_white_horse', 'Vale of White Horse Gliding Club', 51.606980000000000, -1.669490000000000, 108),
('welland', 'Welland Gliding club', 52.463600000000000, -0.583090000000000, 93),
('wolds', 'Wolds Gliding Club', 53.921760000000000, -0.791430000000000, 25),
('york_gliding_centre', 'York Gliding Centre', 53.942220000000000, -1.189970000000000, 19),
('yorkshire', 'Yorkshire Gliding Club', 54.228830000000000, -1.209640000000000, 283),
('syerston', 'Syerston', 53.024159, -0.91171, 69);