import requests
from uuid import uuid4


JsonObject = dict[str, object]


class CoffeeApiError(Exception):
    pass


class CoffeeNotFoundError(CoffeeApiError):
    pass


class SampleApisCoffeeClient:
    def __init__(
        self,
        base_url: str = "https://api.sampleapis.com/coffee/hot",
        timeout: float = 10.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def list_drinks(self) -> list[JsonObject]:
        response = self._request('GET')
        return response.json()

    def get_drink(self, drink_id: int) -> JsonObject:
        response = self._request('GET', f'/{drink_id}')
        return response.json()

    def create_drink(self, payload: JsonObject) -> JsonObject:
        response = self._request('POST', payload=payload)
        return response.json()

    def replace_drink(
        self,
        drink_id: int,
        payload: JsonObject,
    ) -> JsonObject:
        response = self._request('PUT', f'/{drink_id}', payload=payload)
        return response.json()

    def update_drink(
        self,
        drink_id: int,
        changes: JsonObject,
    ) -> JsonObject:
        response = self._request("PATCH", f"/{drink_id}", payload=changes)
        return response.json()

    def delete_drink(self, drink_id: int) -> None:
        self._request("DELETE", f"/{drink_id}")

    def _request(
        self,
        method: str,
        path: str = "",
        payload: JsonObject | None = None,
    ) -> requests.Response:
        url = f'{self._base_url}{path}'
        try:
            response = requests.request(
                method=method,
                url=url,
                json=payload,
                timeout=self._timeout,
            )
        except requests.Timeout as error:
            raise CoffeeApiError(f"Тайм-аут ошибка") from error
        except requests.RequestException as error:
            raise CoffeeApiError(
                f"Сетевая ошибка") from error
        if response.status_code == 404:
            raise CoffeeNotFoundError(f"Ресурс не найден")

        if not response.ok:
            raise CoffeeApiError(
                f"Ошибка API: {response.status_code}"
            )
        if method != "DELETE" and response.text.strip():
            content_type = response.headers.get("Content-Type", "")
            if "application/json" not in content_type:
                raise CoffeeApiError(
                    f"Ожидался JSON, получен {content_type}"
                )
        return response





def main() -> int:
    client = SampleApisCoffeeClient()
    marker = uuid4().hex[:8]
    created_id: int | None = None

    try:
        # 1. GET: получаем список напитков.
        drinks = client.list_drinks()

        if not isinstance(drinks, list):
            raise CoffeeApiError("Expected a list of drinks")

        print(f"Получено напитков: {len(drinks)}")

        # 2. POST: создаём тестовый напиток.
        payload: JsonObject = {
            "title": f"Test Coffee {marker}",
            "description": "Test description",
            "ingredients": ["Water", "Coffee"],
            "image": "https://example.com/test-coffee.jpg",
        }

        created_drink = client.create_drink(payload)

        if not isinstance(created_drink, dict):
            raise CoffeeApiError("POST did not return a JSON object")

        if "id" not in created_drink:
            raise CoffeeApiError("POST response does not contain id")

        # Сохраняем ID сразу после успешного создания.
        created_id = created_drink["id"]

        if not isinstance(created_id, int):
            raise ValueError("Created drink id is not an integer")

        print(f"Создан напиток с id={created_id}")

        # 3. GET: проверяем созданный напиток.
        drink = client.get_drink(created_id)

        for key, value in payload.items():
            if drink.get(key) != value:
                raise CoffeeApiError(
                    f"POST verification failed for field {key}"
                )

        print("POST и GET: проверка пройдена")

        # 4. PUT: полностью заменяем данные напитка.
        replacement_payload: JsonObject = {
            "title": f"Replaced Coffee {marker}",
            "description": "Replaced description",
            "ingredients": ["Milk", "Coffee"],
            "image": "https://example.com/replaced-coffee.jpg",
        }

        client.replace_drink(created_id, replacement_payload)

        # Проверяем результат PUT отдельным GET.
        drink = client.get_drink(created_id)

        for key, value in replacement_payload.items():
            if drink.get(key) != value:
                raise CoffeeApiError(
                    f"PUT verification failed for field {key}"
                )

        print("PUT и GET: проверка пройдена")

        # 5. PATCH: меняем только название.
        patched_title = f"Patched Coffee {marker}"

        client.update_drink(
            created_id,
            {"title": patched_title},
        )

        # Проверяем изменённое поле и сохранность остальных.
        drink = client.get_drink(created_id)

        if drink.get("title") != patched_title:
            raise CoffeeApiError("PATCH did not change the title")

        for key, value in replacement_payload.items():
            if key != "title" and drink.get(key) != value:
                raise CoffeeApiError(
                    f"PATCH changed or lost field {key}"
                )

        print("PATCH и GET: проверка пройдена")

        # 6. DELETE: удаляем созданный напиток.
        client.delete_drink(created_id)
        print("DELETE: запрос выполнен")

        # 7. GET: убеждаемся, что напиток больше не существует.
        try:
            client.get_drink(created_id)
        except CoffeeNotFoundError:
            print("GET после DELETE: получен ожидаемый 404")
            created_id = None
        else:
            raise CoffeeApiError(
                "Drink still exists after DELETE"
            )

        print("Все этапы сценария пройдены")
        return 0

    except (CoffeeApiError, ValueError) as error:
        print(f"Ошибка: {error}. Метка группы: {marker}")
        return 1

    finally:
        # Если сценарий прервался до подтверждения удаления,
        # пытаемся убрать созданную запись.
        if created_id is not None:
            try:
                client.delete_drink(created_id)
                print(f"Очистка: удалён id={created_id}")
            except CoffeeNotFoundError:
                pass
            except CoffeeApiError as error:
                print(
                    f"Не удалось удалить id={created_id}: {error}"
                )


if __name__ == "__main__":
    raise SystemExit(main())
