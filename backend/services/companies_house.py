"""
Companies House API client
"""
import requests
import time
from typing import List, Dict, Any, Optional
import logging

from config import (
    COMPANIES_HOUSE_API_KEY,
    COMPANIES_HOUSE_BASE_URL,
    ITEMS_PER_PAGE,
    RATE_LIMIT_DELAY,
    RATE_LIMIT_BACKOFF
)

logger = logging.getLogger(__name__)

# SIC code descriptions mapping
SIC_DESCRIPTIONS = {
    "01110": "Growing of cereals and other crops",
    "01120": "Growing of rice",
    "01130": "Growing of vegetables, fruits and nuts",
    "01140": "Growing of sugar cane",
    "01150": "Growing of tobacco",
    "01160": "Growing of fibre crops",
    "01190": "Growing of other crops",
    "01210": "Farming of cattle",
    "01220": "Other animal farming",
    "01230": "Mixed farming",
    "01240": "Agricultural services",
    "01250": "Hunting",
    "01300": "Hunting and related service activities",
    "01410": "Growing of crops combined with farming of animals",
    "01420": "Agricultural and animal husbandry service activities",
    "01500": "Hunting, trapping and game propagation",
    "02100": "Forestry and logging",
    "02200": "Logging",
    "05100": "Mining of hard coal",
    "05200": "Mining of lignite",
    "06100": "Extraction of crude petroleum",
    "06200": "Extraction of natural gas",
    "07100": "Mining of iron ores",
    "07210": "Mining of uranium and thorium ores",
    "07290": "Mining of other non-ferrous metal ores",
    "08110": "Quarrying of stone, sand and clay",
    "08120": "Operation of gravel and sand pits",
    "08910": "Mining of chemical and fertiliser minerals",
    "08920": "Extraction of peat",
    "08990": "Other mining and quarrying",
    "09100": "Support activities for petroleum and natural gas extraction",
    "09900": "Support activities for other mining and quarrying",
    "10110": "Processing and preserving of meat",
    "10120": "Processing and preserving of poultry meat",
    "10130": "Production of meat and poultry meat products",
    "10200": "Processing and preserving of fish",
    "10310": "Processing and preserving of potatoes",
    "10320": "Manufacture of fruit and vegetable juice",
    "10390": "Other processing and preserving of fruit and vegetables",
    "10410": "Manufacture of oils and fats",
    "10420": "Manufacture of margarine and similar edible fats",
    "10510": "Operation of dairies and cheese making",
    "10520": "Manufacture of ice cream",
    "10610": "Manufacture of grain mill products",
    "10620": "Manufacture of starches and starch products",
    "10710": "Manufacture of bread",
    "10720": "Manufacture of rusks and biscuits",
    "10730": "Manufacture of macaroni, noodles, couscous",
    "10810": "Manufacture of sugar",
    "10820": "Manufacture of cocoa, chocolate and sugar confectionery",
    "10830": "Processing of tea and coffee",
    "10840": "Manufacture of condiments and seasonings",
    "10850": "Manufacture of prepared meals and dishes",
    "10860": "Manufacture of homogenised food preparations",
    "10890": "Manufacture of other food products",
    "10910": "Manufacture of prepared feeds for farm animals",
    "10920": "Manufacture of prepared pet foods",
    "11010": "Distilling, rectifying and blending of spirits",
    "11020": "Manufacture of wine from grape",
    "11030": "Manufacture of cider and other fruit wines",
    "11040": "Manufacture of other non-distilled fermented beverages",
    "11050": "Manufacture of beer",
    "11060": "Manufacture of malt",
    "11070": "Manufacture of soft drinks",
    "12000": "Manufacture of tobacco products",
    "13100": "Preparation and spinning of textile fibres",
    "13200": "Weaving of textiles",
    "13300": "Finishing of textiles",
    "13910": "Manufacture of knitted and crocheted fabrics",
    "13920": "Manufacture of made-up textile articles",
    "13930": "Manufacture of carpets and rugs",
    "13940": "Manufacture of cordage, rope, twine and netting",
    "13950": "Manufacture of non-wovens and articles made from non-wovens",
    "13960": "Manufacture of other technical and industrial textiles",
    "13990": "Manufacture of other textiles",
    "14110": "Manufacture of leather clothes",
    "14120": "Manufacture of workwear",
    "14130": "Manufacture of other outerwear",
    "14140": "Manufacture of underwear",
    "14190": "Manufacture of other wearing apparel and accessories",
    "14200": "Manufacture of articles of fur",
    "14310": "Manufacture of knitted and crocheted hosiery",
    "14390": "Manufacture of other knitted and crocheted apparel",
    "15110": "Tanning and dressing of leather",
    "15120": "Manufacture of luggage, handbags and the like",
    "15200": "Manufacture of footwear",
    "16100": "Sawmilling and planing of wood",
    "16210": "Manufacture of veneer sheets and wood-based panels",
    "16220": "Manufacture of assembled parquet floors",
    "16230": "Manufacture of other builders' carpentry and joinery",
    "16240": "Manufacture of wooden containers",
    "16290": "Manufacture of other products of wood",
    "17110": "Manufacture of pulp",
    "17120": "Manufacture of paper and paperboard",
    "17210": "Manufacture of corrugated paper and paperboard",
    "17220": "Manufacture of household and sanitary goods",
    "17230": "Manufacture of paper stationery",
    "17240": "Manufacture of wallpaper",
    "17290": "Manufacture of other articles of paper and paperboard",
    "18110": "Printing of newspapers",
    "18120": "Other printing",
    "18130": "Pre-press and pre-media services",
    "18140": "Binding and related services",
    "18200": "Reproduction of recorded media",
    "19100": "Manufacture of coke oven products",
    "19200": "Manufacture of refined petroleum products",
    "20110": "Manufacture of industrial gases",
    "20120": "Manufacture of dyes and pigments",
    "20130": "Manufacture of other inorganic basic chemicals",
    "20140": "Manufacture of other organic basic chemicals",
    "20150": "Manufacture of fertilisers and nitrogen compounds",
    "20160": "Manufacture of plastics in primary forms",
    "20170": "Manufacture of synthetic rubber in primary forms",
    "20200": "Manufacture of pesticides and other agrochemical products",
    "20300": "Manufacture of paints, varnishes and similar coatings",
    "20410": "Manufacture of soap and detergents",
    "20420": "Manufacture of perfumes and toilet preparations",
    "20510": "Manufacture of explosives",
    "20520": "Manufacture of glues",
    "20530": "Manufacture of essential oils",
    "20590": "Manufacture of other chemical products",
    "20600": "Manufacture of man-made fibres",
    "21100": "Manufacture of basic pharmaceutical products",
    "21200": "Manufacture of pharmaceutical preparations",
    "22110": "Manufacture of rubber tyres and tubes",
    "22190": "Manufacture of other rubber products",
    "22210": "Manufacture of plastic plates, sheets, tubes and profiles",
    "22220": "Manufacture of plastic packing goods",
    "22230": "Manufacture of builders ware of plastic",
    "22290": "Manufacture of other plastic products",
    "23110": "Manufacture of flat glass",
    "23120": "Shaping and processing of flat glass",
    "23130": "Manufacture of hollow glass",
    "23140": "Manufacture of glass fibres",
    "23190": "Manufacture and processing of other glass",
    "23200": "Manufacture of refractory products",
    "23310": "Manufacture of ceramic tiles and flags",
    "23320": "Manufacture of bricks, tiles and construction products",
    "23410": "Manufacture of ceramic household and ornamental articles",
    "23420": "Manufacture of ceramic sanitary fixtures",
    "23430": "Manufacture of ceramic insulators",
    "23440": "Manufacture of other technical ceramic products",
    "23490": "Manufacture of other ceramic products",
    "23510": "Manufacture of cement",
    "23520": "Manufacture of lime and plaster",
    "23610": "Manufacture of concrete products for construction",
    "23620": "Manufacture of plaster products for construction",
    "23630": "Manufacture of ready-mixed concrete",
    "23640": "Manufacture of mortars",
    "23650": "Manufacture of fibre cement",
    "23690": "Manufacture of other articles of concrete, plaster and cement",
    "23700": "Cutting, shaping and finishing of stone",
    "23910": "Production of abrasive products",
    "23990": "Manufacture of other non-metallic mineral products",
    "24100": "Manufacture of basic iron and steel",
    "24200": "Manufacture of tubes, pipes, hollow profiles and related fittings",
    "24310": "Cold drawing of bars",
    "24320": "Cold rolling of narrow strip",
    "24330": "Cold forming or folding",
    "24340": "Cold drawing of wire",
    "24410": "Precious metals production",
    "24420": "Aluminium production",
    "24430": "Lead, zinc and tin production",
    "24440": "Copper production",
    "24450": "Other non-ferrous metal production",
    "24460": "Processing of nuclear fuel",
    "24510": "Casting of iron",
    "24520": "Casting of steel",
    "24530": "Casting of light metals",
    "24540": "Casting of other non-ferrous metals",
    "25110": "Manufacture of metal structures and parts of structures",
    "25120": "Manufacture of doors and windows of metal",
    "25210": "Manufacture of central heating radiators and boilers",
    "25290": "Manufacture of other tanks, reservoirs and containers",
    "25300": "Manufacture of steam generators",
    "25400": "Manufacture of weapons and ammunition",
    "25500": "Forging, pressing, stamping and roll-forming of metal",
    "25610": "Treatment and coating of metals",
    "25620": "Machining",
    "25710": "Manufacture of cutlery",
    "25720": "Manufacture of locks and hinges",
    "25730": "Manufacture of tools",
    "25910": "Manufacture of steel drums and similar containers",
    "25920": "Manufacture of light metal packaging",
    "25930": "Manufacture of wire products, chain and springs",
    "25940": "Manufacture of fasteners and screw machine products",
    "25990": "Manufacture of other fabricated metal products",
    "26110": "Manufacture of electronic components",
    "26120": "Manufacture of loaded electronic boards",
    "26200": "Manufacture of computers and peripheral equipment",
    "26301": "Manufacture of telegraph and telephone apparatus",
    "26309": "Manufacture of other communication equipment",
    "26400": "Manufacture of consumer electronics",
    "26510": "Manufacture of instruments for measuring, testing",
    "26520": "Manufacture of watches and clocks",
    "26600": "Manufacture of irradiation, electromedical equipment",
    "26700": "Manufacture of optical instruments and photographic equipment",
    "26800": "Manufacture of magnetic and optical media",
    "27110": "Manufacture of electric motors, generators and transformers",
    "27120": "Manufacture of electricity distribution and control apparatus",
    "27200": "Manufacture of batteries and accumulators",
    "27310": "Manufacture of fibre optic cables",
    "27320": "Manufacture of other electronic and electric wires and cables",
    "27330": "Manufacture of wiring devices",
    "27400": "Manufacture of electric lighting equipment",
    "27510": "Manufacture of electric domestic appliances",
    "27520": "Manufacture of non-electric domestic appliances",
    "27900": "Manufacture of other electrical equipment",
    "28110": "Manufacture of engines and turbines",
    "28120": "Manufacture of fluid power equipment",
    "28130": "Manufacture of other pumps and compressors",
    "28140": "Manufacture of other taps and valves",
    "28150": "Manufacture of bearings, gears, gearing and driving elements",
    "28210": "Manufacture of ovens, furnaces and furnace burners",
    "28220": "Manufacture of lifting and handling equipment",
    "28230": "Manufacture of office machinery and equipment",
    "28240": "Manufacture of power-driven hand tools",
    "28250": "Manufacture of non-domestic cooling and ventilation equipment",
    "28290": "Manufacture of other general-purpose machinery",
    "28301": "Manufacture of agricultural tractors",
    "28302": "Manufacture of other agricultural and forestry machinery",
    "28410": "Manufacture of metal forming machinery",
    "28490": "Manufacture of other machine tools",
    "28910": "Manufacture of machinery for metallurgy",
    "28920": "Manufacture of machinery for mining, quarrying",
    "28930": "Manufacture of machinery for food, beverage processing",
    "28940": "Manufacture of machinery for textile, apparel production",
    "28950": "Manufacture of machinery for paper and paperboard production",
    "28960": "Manufacture of plastics and rubber machinery",
    "28990": "Manufacture of other special-purpose machinery",
    "29100": "Manufacture of motor vehicles",
    "29201": "Manufacture of bodies for motor vehicles",
    "29202": "Manufacture of trailers and semi-trailers",
    "29310": "Manufacture of electrical and electronic equipment for motor vehicles",
    "29320": "Manufacture of other parts and accessories for motor vehicles",
    "30110": "Building of ships and floating structures",
    "30120": "Building of pleasure and sporting boats",
    "30200": "Manufacture of railway locomotives and rolling stock",
    "30300": "Manufacture of air and spacecraft and related machinery",
    "30400": "Manufacture of military fighting vehicles",
    "30910": "Manufacture of motorcycles",
    "30920": "Manufacture of bicycles and invalid carriages",
    "30990": "Manufacture of other transport equipment",
    "31010": "Manufacture of office and shop furniture",
    "31020": "Manufacture of kitchen furniture",
    "31030": "Manufacture of mattresses",
    "31090": "Manufacture of other furniture",
    "32110": "Striking of coins",
    "32120": "Manufacture of jewellery and related articles",
    "32130": "Manufacture of imitation jewellery and related articles",
    "32200": "Manufacture of musical instruments",
    "32300": "Manufacture of sports goods",
    "32400": "Manufacture of games and toys",
    "32500": "Manufacture of medical and dental instruments and supplies",
    "32910": "Manufacture of brooms and brushes",
    "32990": "Other manufacturing",
    "33110": "Repair of fabricated metal products",
    "33120": "Repair of machinery",
    "33130": "Repair of electronic and optical equipment",
    "33140": "Repair of electrical equipment",
    "33150": "Repair and maintenance of ships and boats",
    "33160": "Repair and maintenance of aircraft and spacecraft",
    "33170": "Repair and maintenance of other transport equipment",
    "33190": "Repair of other equipment",
    "33200": "Installation of industrial machinery and equipment",
    "35110": "Production of electricity",
    "35120": "Transmission of electricity",
    "35130": "Distribution of electricity",
    "35140": "Trade of electricity",
    "35210": "Manufacture of gas",
    "35220": "Distribution of gaseous fuels through mains",
    "35230": "Trade of gas through mains",
    "35300": "Steam and air conditioning supply",
    "36000": "Water collection, treatment and supply",
    "37000": "Sewerage",
    "38110": "Collection of non-hazardous waste",
    "38120": "Collection of hazardous waste",
    "38210": "Treatment and disposal of non-hazardous waste",
    "38220": "Treatment and disposal of hazardous waste",
    "38310": "Dismantling of wrecks",
    "38320": "Recovery of sorted materials",
    "39000": "Remediation activities and other waste management services",
    "41100": "Development of building projects",
    "41201": "Construction of commercial buildings",
    "41202": "Construction of domestic buildings",
    "42110": "Construction of roads and motorways",
    "42120": "Construction of railways and underground railways",
    "42130": "Construction of bridges and tunnels",
    "42210": "Construction of utility projects for fluids",
    "42220": "Construction of utility projects for electricity",
    "42910": "Construction of water projects",
    "42990": "Construction of other civil engineering projects",
    "43110": "Demolition",
    "43120": "Site preparation",
    "43130": "Test drilling and boring",
    "43210": "Electrical installation",
    "43220": "Plumbing, heat and air-conditioning installation",
    "43290": "Other construction installation",
    "43310": "Plastering",
    "43320": "Joinery installation",
    "43330": "Floor and wall covering",
    "43341": "Painting",
    "43342": "Glazing",
    "43390": "Other building completion and finishing",
    "43910": "Roofing activities",
    "43991": "Scaffold erection",
    "43999": "Other specialised construction activities",
    "45111": "Sale of new cars and light motor vehicles",
    "45112": "Sale of used cars and light motor vehicles",
    "45190": "Sale of other motor vehicles",
    "45200": "Maintenance and repair of motor vehicles",
    "45310": "Wholesale trade of motor vehicle parts and accessories",
    "45320": "Retail trade of motor vehicle parts and accessories",
    "45400": "Sale, maintenance and repair of motorcycles",
    "46110": "Agents involved in the sale of agricultural raw materials",
    "46120": "Agents involved in the sale of fuels, ores, metals and chemicals",
    "46130": "Agents involved in the sale of timber and building materials",
    "46140": "Agents involved in the sale of machinery, equipment",
    "46150": "Agents involved in the sale of furniture, household goods",
    "46160": "Agents involved in the sale of textiles, clothing, fur, footwear",
    "46170": "Agents involved in the sale of food, beverages and tobacco",
    "46180": "Agents specialised in the sale of other particular products",
    "46190": "Agents involved in the sale of a variety of goods",
    "46210": "Wholesale of grain, unmanufactured tobacco, seeds and animal feeds",
    "46220": "Wholesale of flowers and plants",
    "46230": "Wholesale of live animals",
    "46240": "Wholesale of hides, skins and leather",
    "46310": "Wholesale of fruit and vegetables",
    "46320": "Wholesale of meat and meat products",
    "46330": "Wholesale of dairy products, eggs and edible oils and fats",
    "46340": "Wholesale of beverages",
    "46350": "Wholesale of tobacco products",
    "46360": "Wholesale of sugar and chocolate and sugar confectionery",
    "46370": "Wholesale of coffee, tea, cocoa and spices",
    "46380": "Wholesale of other food, including fish, crustaceans and molluscs",
    "46390": "Non-specialised wholesale of food, beverages and tobacco",
    "46410": "Wholesale of textiles",
    "46420": "Wholesale of clothing and footwear",
    "46430": "Wholesale of electrical household appliances",
    "46440": "Wholesale of china and glassware and cleaning materials",
    "46450": "Wholesale of perfume and cosmetics",
    "46460": "Wholesale of pharmaceutical goods",
    "46470": "Wholesale of furniture, carpets and lighting equipment",
    "46480": "Wholesale of watches and jewellery",
    "46490": "Wholesale of other household goods",
    "46510": "Wholesale of computers, computer peripheral equipment and software",
    "46520": "Wholesale of electronic and telecommunications equipment",
    "46610": "Wholesale of agricultural machinery, equipment and supplies",
    "46620": "Wholesale of machine tools",
    "46630": "Wholesale of mining, construction and civil engineering machinery",
    "46640": "Wholesale of machinery for the textile industry",
    "46650": "Wholesale of office furniture",
    "46660": "Wholesale of other office machinery and equipment",
    "46690": "Wholesale of other machinery and equipment",
    "46711": "Wholesale of petroleum and petroleum products",
    "46719": "Wholesale of other fuels and related products",
    "46720": "Wholesale of metals and metal ores",
    "46730": "Wholesale of wood, construction materials and sanitary equipment",
    "46740": "Wholesale of hardware, plumbing and heating equipment",
    "46750": "Wholesale of chemical products",
    "46760": "Wholesale of other intermediate products",
    "46770": "Wholesale of waste and scrap",
    "46900": "Non-specialised wholesale trade",
    "47110": "Retail sale in non-specialised stores",
    "47190": "Other retail sale in non-specialised stores",
    "47210": "Retail sale of fruit and vegetables",
    "47220": "Retail sale of meat and meat products",
    "47230": "Retail sale of fish, crustaceans and molluscs",
    "47240": "Retail sale of bread, cakes, flour confectionery and sugar confectionery",
    "47250": "Retail sale of beverages",
    "47260": "Retail sale of tobacco products",
    "47290": "Other retail sale of food in specialised stores",
    "47300": "Retail sale of automotive fuel",
    "47410": "Retail sale of computers, peripheral units and software",
    "47421": "Retail sale of mobile telephones",
    "47429": "Retail sale of telecommunications equipment other than mobile telephones",
    "47430": "Retail sale of audio and video equipment",
    "47510": "Retail sale of textiles",
    "47520": "Retail sale of hardware, paints and glass",
    "47530": "Retail sale of carpets, rugs, wall and floor coverings",
    "47540": "Retail sale of electrical household appliances",
    "47591": "Retail sale of musical instruments and scores",
    "47599": "Retail of furniture, lighting, and similar",
    "47610": "Retail sale of books",
    "47620": "Retail sale of newspapers and stationery",
    "47630": "Retail sale of music and video recordings",
    "47640": "Retail sale of sports goods",
    "47650": "Retail sale of games and toys",
    "47710": "Retail sale of clothing",
    "47721": "Retail sale of footwear",
    "47722": "Retail sale of leather goods",
    "47730": "Dispensing chemist",
    "47741": "Retail sale of hearing aids",
    "47749": "Retail sale of medical and orthopaedic goods",
    "47750": "Retail sale of cosmetic and toilet articles",
    "47760": "Retail sale of flowers, plants, seeds, fertilisers",
    "47770": "Retail sale of watches and jewellery",
    "47781": "Retail sale of computers, peripheral units and software",
    "47782": "Retail sale by opticians",
    "47789": "Other retail sale of new goods in specialised stores",
    "47791": "Retail sale of antiques including antique books",
    "47799": "Retail sale of other second-hand goods",
    "47810": "Retail sale via stalls and markets of food, beverages and tobacco",
    "47820": "Retail sale via stalls and markets of textiles, clothing and footwear",
    "47890": "Retail sale via stalls and markets of other goods",
    "47910": "Retail sale via mail order houses or via Internet",
    "47990": "Other retail sale not in stores, stalls or markets",
    "49100": "Passenger rail transport, interurban",
    "49200": "Freight rail transport",
    "49311": "Urban and suburban passenger railway transportation by underground",
    "49319": "Other urban and suburban passenger land transport",
    "49320": "Taxi operation",
    "49390": "Other passenger land transport",
    "49410": "Freight transport by road",
    "49420": "Removal services",
    "49500": "Transport via pipeline",
    "50100": "Sea and coastal passenger water transport",
    "50200": "Sea and coastal freight water transport",
    "50300": "Inland passenger water transport",
    "50400": "Inland freight water transport",
    "51101": "Scheduled passenger air transport",
    "51102": "Non-scheduled passenger air transport",
    "51210": "Freight air transport",
    "51220": "Space transport",
    "52101": "Operation of warehousing and storage facilities for land transport",
    "52102": "Operation of warehousing and storage facilities for water transport",
    "52103": "Operation of warehousing and storage facilities for air transport",
    "52211": "Operation of rail freight terminals",
    "52212": "Operation of rail passenger facilities at railway stations",
    "52213": "Operation of bus and coach passenger facilities",
    "52219": "Other service activities incidental to land transportation",
    "52220": "Service activities incidental to water transportation",
    "52230": "Service activities incidental to air transportation",
    "52241": "Cargo handling for water transport activities",
    "52242": "Cargo handling for land transport activities",
    "52243": "Cargo handling for air transport activities",
    "52290": "Other transportation support activities",
    "53100": "Postal activities under universal service obligation",
    "53201": "Licensed carriers",
    "53202": "Unlicensed carriers",
    "55100": "Hotels and similar accommodation",
    "55201": "Holiday centres and villages",
    "55202": "Youth hostels",
    "55209": "Other holiday and other collective accommodation",
    "55300": "Recreational vehicle parks, trailer parks and camping grounds",
    "55900": "Other accommodation",
    "56101": "Licensed restaurants",
    "56102": "Unlicensed restaurants and cafes",
    "56103": "Take-away food shops and mobile food stands",
    "56210": "Event catering activities",
    "56290": "Other food service activities",
    "56301": "Licensed clubs",
    "56302": "Public houses and bars",
    "58110": "Book publishing",
    "58120": "Publishing of directories and mailing lists",
    "58130": "Publishing of newspapers",
    "58140": "Publishing of journals and periodicals",
    "58190": "Other publishing activities",
    "58210": "Publishing of computer games",
    "58290": "Other software publishing",
    "59111": "Motion picture production activities",
    "59112": "Video production activities",
    "59113": "Television programme production activities",
    "59120": "Motion picture, video and television programme post-production",
    "59131": "Motion picture distribution activities",
    "59132": "Video distribution activities",
    "59133": "Television programme distribution activities",
    "59140": "Motion picture projection activities",
    "59200": "Sound recording and music publishing activities",
    "60100": "Radio broadcasting",
    "60200": "Television programming and broadcasting activities",
    "61100": "Wired telecommunications activities",
    "61200": "Wireless telecommunications activities",
    "61300": "Satellite telecommunications activities",
    "61900": "Other telecommunications activities",
    "62011": "Ready-made interactive leisure and entertainment software development",
    "62012": "Business and domestic software development",
    "62020": "Information technology consultancy activities",
    "62030": "Computer facilities management activities",
    "62090": "Other information technology service activities",
    "63110": "Data processing, hosting and related activities",
    "63120": "Web portals",
    "63910": "News agency activities",
    "63990": "Other information service activities",
    "64110": "Central banking",
    "64191": "Banks",
    "64192": "Building societies",
    "64201": "Activities of agricultural holding companies",
    "64202": "Activities of production holding companies",
    "64203": "Activities of construction holding companies",
    "64204": "Activities of distribution holding companies",
    "64205": "Activities of financial services holding companies",
    "64209": "Activities of other holding companies",
    "64301": "Activities of investment trusts",
    "64302": "Activities of unit trusts",
    "64303": "Activities of venture and development capital companies",
    "64304": "Activities of open-ended investment companies",
    "64305": "Activities of property unit trusts",
    "64306": "Activities of real estate investment trusts",
    "64910": "Financial leasing",
    "64921": "Credit granting by non-deposit taking finance houses",
    "64922": "Activities of mortgage finance companies",
    "64929": "Other credit granting",
    "64991": "Security dealing on own account",
    "64992": "Factoring",
    "64999": "Other financial service activities",
    "65110": "Life insurance",
    "65120": "Non-life insurance",
    "65201": "Life reinsurance",
    "65202": "Non-life reinsurance",
    "65300": "Pension funding",
    "66110": "Administration of financial markets",
    "66120": "Security and commodity contracts dealing activities",
    "66190": "Other activities auxiliary to financial intermediation",
    "66210": "Risk and damage evaluation",
    "66220": "Activities of insurance agents and brokers",
    "66290": "Other activities auxiliary to insurance and pension funding",
    "66300": "Fund management activities",
    "68100": "Buying and selling of own real estate",
    "68201": "Renting and operating of Housing Association real estate",
    "68202": "Letting and operating of conference and exhibition centres",
    "68209": "Other letting and operating of own or leased real estate",
    "68310": "Real estate agencies",
    "68320": "Management of real estate on a fee or contract basis",
    "69101": "Barristers at law",
    "69102": "Solicitors",
    "69109": "Other legal activities",
    "69201": "Accounting and auditing activities",
    "69202": "Bookkeeping activities",
    "69203": "Tax consultancy",
    "70100": "Activities of head offices",
    "70210": "Public relations and communications activities",
    "70221": "Financial management",
    "70229": "Other management consultancy activities",
    "71111": "Architectural activities",
    "71112": "Urban planning and landscape architectural activities",
    "71121": "Engineering design activities for industrial process and production",
    "71122": "Engineering related scientific and technical consulting activities",
    "71129": "Other engineering activities",
    "71200": "Technical testing and analysis",
    "72110": "Research and experimental development on biotechnology",
    "72190": "Other research and experimental development on natural sciences",
    "72200": "Research and experimental development on social sciences and humanities",
    "73110": "Advertising agencies",
    "73120": "Media representation services",
    "73200": "Market research and public opinion polling",
    "74100": "Specialised design activities",
    "74201": "Portrait photographic activities",
    "74202": "Other specialist photography",
    "74203": "Film processing",
    "74209": "Other photographic activities",
    "74300": "Translation and interpretation activities",
    "74901": "Environmental consulting activities",
    "74902": "Quantity surveying activities",
    "74909": "Other professional, scientific and technical activities",
    "74990": "Other professional, scientific and technical activities",
    "75000": "Veterinary activities",
    "77110": "Renting and leasing of cars and light motor vehicles",
    "77120": "Renting and leasing of trucks",
    "77210": "Renting and leasing of recreational and sports goods",
    "77220": "Renting of video tapes and disks",
    "77290": "Renting and leasing of other personal and household goods",
    "77310": "Renting and leasing of agricultural machinery and equipment",
    "77320": "Renting and leasing of construction and civil engineering machinery",
    "77330": "Renting and leasing of office machinery and equipment",
    "77340": "Renting and leasing of water transport equipment",
    "77350": "Renting and leasing of air transport equipment",
    "77390": "Renting and leasing of other machinery, equipment and tangible goods",
    "77400": "Leasing of intellectual property and similar products",
    "78101": "Motion picture, television and other theatrical casting",
    "78109": "Other activities of employment placement agencies",
    "78200": "Temporary employment agency activities",
    "78300": "Human resources provision and management of human resources functions",
    "79110": "Travel agency activities",
    "79120": "Tour operator activities",
    "79901": "Tourism activities",
    "79909": "Other reservation service activities",
    "80100": "Private security activities",
    "80200": "Security systems service activities",
    "80300": "Investigation activities",
    "81100": "Combined facilities support activities",
    "81210": "General cleaning of buildings",
    "81221": "Window cleaning services",
    "81222": "Specialised cleaning services",
    "81223": "Furnace and chimney cleaning services",
    "81229": "Other building and industrial cleaning activities",
    "81291": "Disinfecting and exterminating services",
    "81299": "Other cleaning services",
    "81300": "Landscape service activities",
    "82110": "Combined office administrative service activities",
    "82190": "Photocopying, document preparation and other office support activities",
    "82200": "Activities of call centres",
    "82301": "Activities of exhibition and fair organisers",
    "82302": "Activities of conference organisers",
    "82911": "Activities of collection agencies",
    "82912": "Activities of credit bureaus",
    "82920": "Packaging activities",
    "82990": "Other business support service activities",
    "84110": "General public administration activities",
    "84120": "Regulation of health care, education, cultural and other social services",
    "84130": "Regulation of and contribution to more efficient operation of businesses",
    "84210": "Foreign affairs",
    "84220": "Defence activities",
    "84230": "Justice and judicial activities",
    "84240": "Public order and safety activities",
    "84250": "Fire service activities",
    "84300": "Compulsory social security activities",
    "85100": "Pre-primary education",
    "85200": "Primary education",
    "85310": "General secondary education",
    "85320": "Technical and vocational secondary education",
    "85410": "Post-secondary non-tertiary education",
    "85421": "First-degree level higher education",
    "85422": "Post-graduate level higher education",
    "85510": "Sports and recreation education",
    "85520": "Cultural education",
    "85530": "Driving school activities",
    "85590": "Other education",
    "85600": "Educational support activities",
    "86101": "Hospital activities",
    "86102": "Medical nursing home activities",
    "86210": "General medical practice activities",
    "86220": "Specialists medical practice activities",
    "86230": "Dental practice activities",
    "86900": "Other human health activities",
    "87100": "Residential nursing care activities",
    "87200": "Residential care activities for learning disabilities, mental health and substance abuse",
    "87300": "Residential care activities for the elderly and disabled",
    "87900": "Other residential care activities",
    "88100": "Social work activities without accommodation for the elderly and disabled",
    "88910": "Child day-care activities",
    "88990": "Other social work activities without accommodation",
    "90010": "Performing arts",
    "90020": "Support activities to performing arts",
    "90030": "Artistic creation",
    "90040": "Operation of arts facilities",
    "91011": "Library activities",
    "91012": "Archives activities",
    "91020": "Museums activities",
    "91030": "Operation of historical sites and buildings and similar visitor attractions",
    "91040": "Botanical and zoological gardens and nature reserves activities",
    "92000": "Gambling and betting activities",
    "93110": "Operation of sports facilities",
    "93120": "Activities of sport clubs",
    "93130": "Fitness facilities",
    "93191": "Activities of racehorse owners",
    "93199": "Other sports activities",
    "93210": "Activities of amusement parks and theme parks",
    "93290": "Other amusement and recreation activities",
    "94110": "Activities of business and employers membership organisations",
    "94120": "Activities of professional membership organisations",
    "94200": "Activities of trade unions",
    "94910": "Activities of religious organisations",
    "94920": "Activities of political organisations",
    "94990": "Activities of other membership organisations",
    "95110": "Repair of computers and peripheral equipment",
    "95120": "Repair of communication equipment",
    "95210": "Repair of consumer electronics",
    "95220": "Repair of household appliances and home and garden equipment",
    "95230": "Repair of footwear and leather goods",
    "95240": "Repair of furniture and home furnishings",
    "95250": "Repair of watches, clocks and jewellery",
    "95290": "Repair of other personal and household goods",
    "96010": "Washing and (dry-)cleaning of textile and fur products",
    "96020": "Hairdressing and other beauty treatment",
    "96030": "Funeral and related activities",
    "96040": "Physical well-being activities",
    "96090": "Other personal service activities",
    "97000": "Activities of households as employers of domestic personnel",
    "98000": "Undifferentiated goods-producing activities of private households",
    "98200": "Undifferentiated service-producing activities of private households",
    "99000": "Activities of extraterritorial organisations and bodies",
    "99999": "Dormant Company"
}


class CompaniesHouseAPI:
    """Client for Companies House API"""

    def __init__(self):
        self.base_url = COMPANIES_HOUSE_BASE_URL
        self.api_key = COMPANIES_HOUSE_API_KEY
        self.session = requests.Session()
        self.session.auth = (self.api_key, '')

    def search_by_sic_codes(
        self,
        sic_codes: List[str],
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search companies by SIC codes.
        Returns all companies matching any of the provided SIC codes.
        """
        all_companies = []
        seen_company_numbers = set()

        for sic_code in sic_codes:
            logger.info(f"Searching SIC code: {sic_code}")
            companies = self._search_single_sic(sic_code, active_only)

            # Deduplicate
            for company in companies:
                company_num = company.get('company_number')
                if company_num and company_num not in seen_company_numbers:
                    seen_company_numbers.add(company_num)
                    all_companies.append(company)

            logger.info(f"SIC {sic_code}: Found {len(companies)} companies (total unique: {len(all_companies)})")

        return all_companies

    def search_by_company_name(
        self,
        search_term: str,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search companies by company name.
        Returns all companies matching the search term.
        """
        companies = []
        start_index = 0

        logger.info(f"Searching for company name: {search_term}")

        while True:
            params = {
                'q': search_term,
                'size': ITEMS_PER_PAGE,
                'start_index': start_index
            }

            if active_only:
                params['company_status'] = 'active'

            try:
                response = self._make_request('/advanced-search/companies', params)

                if response is None:
                    break

                items = response.get('items', [])
                if not items:
                    break

                # Process each company
                for item in items:
                    company = self._process_company(item)
                    companies.append(company)

                # Check if we've reached the end
                hits = response.get('hits', 0)
                start_index += len(items)

                logger.info(f"Search '{search_term}': fetched {start_index}/{hits} companies")

                if start_index >= hits or start_index >= 10000:  # API limit
                    break

                time.sleep(RATE_LIMIT_DELAY)

            except Exception as e:
                logger.error(f"Error searching company name '{search_term}': {e}")
                break

        logger.info(f"Search '{search_term}': Found {len(companies)} total companies")
        return companies

    def _search_single_sic(
        self,
        sic_code: str,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """Search companies for a single SIC code with pagination."""
        companies = []
        start_index = 0

        while True:
            params = {
                'sic_codes': sic_code,
                'size': ITEMS_PER_PAGE,
                'start_index': start_index
            }

            if active_only:
                params['company_status'] = 'active'

            try:
                response = self._make_request('/advanced-search/companies', params)

                if response is None:
                    break

                items = response.get('items', [])
                if not items:
                    break

                # Process each company
                for item in items:
                    company = self._process_company(item)
                    companies.append(company)

                # Check if we've reached the end
                hits = response.get('hits', 0)
                start_index += len(items)

                if start_index >= hits or start_index >= 10000:  # API limit
                    break

                time.sleep(RATE_LIMIT_DELAY)

            except Exception as e:
                logger.error(f"Error searching SIC {sic_code}: {e}")
                break

        return companies

    def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Make a request to the Companies House API with retry logic."""
        url = f"{self.base_url}{endpoint}"
        max_retries = 3

        for attempt in range(max_retries):
            try:
                response = self.session.get(url, params=params, timeout=30)

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 416:
                    # Range not satisfiable - reached end of results
                    return None
                elif response.status_code == 429:
                    # Rate limited
                    logger.warning(f"Rate limited, waiting {RATE_LIMIT_BACKOFF}s...")
                    time.sleep(RATE_LIMIT_BACKOFF)
                    continue
                elif response.status_code == 404:
                    logger.warning(f"404 for endpoint {endpoint}")
                    return None
                else:
                    logger.error(f"API error {response.status_code}: {response.text}")
                    if attempt < max_retries - 1:
                        time.sleep(5)
                        continue
                    return None

            except requests.exceptions.RequestException as e:
                logger.error(f"Request error: {e}")
                if attempt < max_retries - 1:
                    time.sleep(5)
                    continue
                return None

        return None

    def _process_company(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Process a company item from the API response."""
        address = item.get('registered_office_address', {})
        sic_codes = item.get('sic_codes', [])

        # Get SIC descriptions
        sic_descriptions = []
        for sic in sic_codes:
            desc = SIC_DESCRIPTIONS.get(sic, 'Unknown')
            sic_descriptions.append(desc)

        return {
            'company_number': item.get('company_number', ''),
            'company_name': item.get('company_name', ''),
            'company_status': item.get('company_status', ''),
            'company_type': item.get('company_type', ''),
            'date_of_creation': item.get('date_of_creation', ''),
            'sic_codes': ', '.join(sic_codes) if sic_codes else '',
            'sic_descriptions': ', '.join(sic_descriptions) if sic_descriptions else '',
            'address_line_1': address.get('address_line_1', ''),
            'address_line_2': address.get('address_line_2', ''),
            'locality': address.get('locality', ''),
            'region': address.get('region', ''),
            'postal_code': address.get('postal_code', ''),
            'country': address.get('country', ''),
            'full_address': self._format_address(address)
        }

    def _format_address(self, address: Dict[str, Any]) -> str:
        """Format address into a single string."""
        parts = [
            address.get('address_line_1', ''),
            address.get('address_line_2', ''),
            address.get('locality', ''),
            address.get('region', ''),
            address.get('postal_code', ''),
            address.get('country', '')
        ]
        return ', '.join(p for p in parts if p)


def get_all_sic_codes() -> List[Dict[str, str]]:
    """Get all SIC codes as a list of dicts for the frontend."""
    return [
        {'code': code, 'description': desc}
        for code, desc in sorted(SIC_DESCRIPTIONS.items())
    ]
