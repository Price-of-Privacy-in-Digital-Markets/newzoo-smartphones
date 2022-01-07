import csv
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from decimal import Decimal
from bs4 import BeautifulSoup

RETRIES = 5
TIMEOUT = 30

class TimeoutHTTPAdapter(HTTPAdapter):
    def __init__(self, *args, **kwargs):
        self.timeout = kwargs.pop("timeout", TIMEOUT)
        super().__init__(*args, **kwargs)

    def send(self, request, **kwargs):
        kwargs.setdefault("timeout", self.timeout)
        return super().send(request, **kwargs)


def make_retryable_session():
    session = requests.Session()
    retries = Retry(total=RETRIES, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    session.mount("http://", TimeoutHTTPAdapter(max_retries=retries))
    session.mount("https://", TimeoutHTTPAdapter(max_retries=retries))
    return session


def convert_population(population: str) -> Decimal:
    if population.endswith("m") or population.endswith("M"):
        return Decimal(population[:-1]) * 10**6
    elif population.endswith("b") or population.endswith("B"):
        return Decimal(population[:-1]) * 10**9
    else:
        raise ValueError(f"Invalid suffix: {population}")


def convert_percentage(percent: str) -> Decimal:
    if percent[-1] != "%":
        raise ValueError(f"Invalid percentage: {percent}")

    return Decimal(percent[:-1]) / 100


def extract_rankings(soup: BeautifulSoup):
    table = soup.find("table", attrs={"id": "ranking"})

    for tr in table.find("tbody").find_all("tr"):
        flag_td, country_td, total_population_td, smartphone_penetration_td, smartphone_users_td = tr.find_all("td")

        yield {
            "country": country_td.text.strip(),
            "total_population": convert_population(total_population_td.text.strip()),
            "smartphone_penetration": convert_percentage(smartphone_penetration_td.text.strip()),
            "smartphone_users": convert_population(smartphone_users_td.text.strip())
        }


if __name__ == "__main__":
    with make_retryable_session() as session:
        r = session.get("https://newzoo.com/insights/rankings/top-countries-by-smartphone-penetration-and-users/")
        r.raise_for_status()

        soup = BeautifulSoup(r.text, features="lxml")

        with open("rankings.csv", "w", newline="\n", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["country", "total_population", "smartphone_penetration", "smartphone_users"])

            writer.writeheader()
            for ranking in extract_rankings(soup):
                writer.writerow(ranking)
