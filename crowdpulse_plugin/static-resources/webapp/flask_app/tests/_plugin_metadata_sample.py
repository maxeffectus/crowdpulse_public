from uuid import UUID

device_id_1 = str(UUID("00000000-00000000-00000000-00000001"))
device_id_2 = str(UUID("00000000-00000000-00000000-00000002"))
engine_id_1 = str(UUID("00000000-00000000-00000001-00000001"))
engine_id_2 = str(UUID("00000000-00000000-00000001-00000002"))


metadata_sample = [
    {
        "deviceId": device_id_1,
        "durationUs": "200000",
        "objectMetadataList": [
            {
                "analyticsEngineId": engine_id_1,
                "boundingBox": {
                    "height": -0.05834949389100075,
                    "width": 0.05932650715112686,
                    "x": 0.17651349306106567,
                    "y": 0.9980469942092896,
                },
                "objectMetadataType": "regular",
                "trackId": "track_id_1",
                "typeId": "nx.nxai.Attentive",
            },
        ],
        "streamIndex": "secondary",
        "timestampUs": "1740850360308100",
    },
    {
        "deviceId": device_id_1,
        "durationUs": "200000",
        "objectMetadataList": [
            {
                "analyticsEngineId": engine_id_1,
                "boundingBox": {
                    "height": 0.2,
                    "width": 0.4,
                    "x": 0.15,
                    "y": 0.56,
                },
                "objectMetadataType": "regular",
                "trackId": "track_id_2",
                "typeId": "nx.nxai.Distracted",
            },
        ],
        "streamIndex": "secondary",
        "timestampUs": "1740850360308100",
    },
    {
        "deviceId": device_id_1,
        "durationUs": "200000",
        "objectMetadataList": [
            {
                "analyticsEngineId": engine_id_1,
                "boundingBox": {
                    "height": 0.3,
                    "width": 0.1,
                    "x": 0.4,
                    "y": 0.35,
                },
                "objectMetadataType": "regular",
                "trackId": "track_id_3",
                "typeId": "some_unknown_type",
            },
        ],
        "streamIndex": "secondary",
        "timestampUs": "1740850360308100",
    },
    {
        "deviceId": device_id_1,
        "durationUs": "200000",
        "objectMetadataList": [
            {
                "analyticsEngineId": engine_id_2,
                "boundingBox": {
                    "height": 0.05,
                    "width": 0.43,
                    "x": 0.6,
                    "y": 0.54,
                },
                "objectMetadataType": "regular",
                "trackId": "track_id_4",
                "typeId": "some_unknown_type",
            },
        ],
        "streamIndex": "secondary",
        "timestampUs": "1740850360308100",
    },
    {
        "deviceId": device_id_2,
        "durationUs": "200000",
        "objectMetadataList": [
            {
                "analyticsEngineId": engine_id_1,
                "boundingBox": {
                    "height": -0.05834949389100075,
                    "width": 0.05932650715112686,
                    "x": 0.17651349306106567,
                    "y": 0.9980469942092896,
                },
                "objectMetadataType": "regular",
                "trackId": "track_id_5",
                "typeId": "nx.nxai.Distracted",
            },
        ],
        "streamIndex": "secondary",
        "timestampUs": "1740850360308100",
    },
    {
        "deviceId": device_id_2,
        "durationUs": "200000",
        "objectMetadataList": [
            {
                "analyticsEngineId": engine_id_1,
                "boundingBox": {
                    "height": 0.2,
                    "width": 0.4,
                    "x": 0.15,
                    "y": 0.56,
                },
                "objectMetadataType": "regular",
                "trackId": "track_id_6",
                "typeId": "nx.nxai.Distracted",
            },
        ],
        "streamIndex": "secondary",
        "timestampUs": "1740850360308100",
    },
]
