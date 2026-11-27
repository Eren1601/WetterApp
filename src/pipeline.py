import openmeteo_requests

import pandas as pd
import requests_cache
from retry_requests import retry

class Pipeline:


    def __init__(self):
        pass

    def extract(self):
        cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
        retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
        openmeteo = openmeteo_requests.Client(session=retry_session)

        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": [50.313, 49.9833, 49.4542],
            "longitude": [11.9126, 11.6333, 11.0775],
            "hourly": ["temperature_2m", "relative_humidity_2m", "precipitation", "apparent_temperature"],
        }
        responses = openmeteo.weather_api(url, params=params)
        cities = ["Hof","Bayreuth","Nürnberg"]

        dataframes = []
        for city,response in zip(cities, responses):
            print(
                f"\nCoordinates: {abs(response.Latitude())}°{'S' if response.Latitude() < 0 else 'N'} {abs(response.Longitude())}°{'W' if response.Longitude() < 0 else 'E'}")
            print(f"Elevation: {response.Elevation()} m asl")
            print(f"Timezone difference to GMT+0: {response.UtcOffsetSeconds()}s")

            # Process hourly data. The order of variables needs to be the same as requested.
            hourly = response.Hourly()
            hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()
            hourly_relative_humidity_2m = hourly.Variables(1).ValuesAsNumpy()
            hourly_precipitation = hourly.Variables(2).ValuesAsNumpy()
            hourly_apparent_temperature = hourly.Variables(3).ValuesAsNumpy()

            hourly_data = {"date": pd.date_range(
                start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
                end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
                freq=pd.Timedelta(seconds=hourly.Interval()),
                inclusive="left"
            ), "temperature_2m": hourly_temperature_2m, "relative_humidity_2m": hourly_relative_humidity_2m,
                "precipitation": hourly_precipitation, "apparent_temperature": hourly_apparent_temperature}

            hourly_dataframe = pd.DataFrame(data=hourly_data)
            hourly_dataframe["city"] = city
            dataframes.append(hourly_dataframe)

        combined_dataframe = pd.concat(dataframes, ignore_index=True)
        return combined_dataframe

    def transform(self, dataframe):
        # Fehlende Werte überprüfen
        print("Fehlende Werte:")
        print(dataframe.isnull().sum())

        # Duplikate entfernen
        dataframe = dataframe.drop_duplicates(
            subset=["date", "city"],
            keep="last"
        )

        # Nach Stadt und Datum sortieren
        dataframe = dataframe.sort_values(
            by=["city", "date"]
        )

        # Index zurücksetzen
        dataframe = dataframe.reset_index(drop=True)

        return dataframe

    def laod(self, dataframe):
