# MVPN ENULATOR
Эмулятор API на python

## Запуск

```bash
$ python main
```

### Допустимые параметры

````
'-t', '--template': Директория с описанием запросов и ответов;
'--placeholders': Путь до файла placeholders.json, данный файл можно использовать;
для подстановки значений, при использовании заглушки '$pl:' (Подробее в пункте "Заглушки");
'-p', '--port': Порт для запуска;
'--host': Адресс для запуска;
````

## Описание описания запроса, ответа
#### Описание должно находится только в формате json

### Пример описания

```json
{
  "name": "example",
  "path": "/example",
  "requests": {
    "get": {
      "request": {
        "headers": {
          "X-User": "..."
        },
        "parameters": {
          "offset": "0",
          "limit": "...",
          "filter": [
            {
              "field": "msisdn",
              "type": "equal",
              "value": "$re:^[0-9]{0,32}$"
            }
          ]
        }
      },
      "response": {
        "status": 200,
        "body": {
          "status": 200,
          "message": "success",
          "data": {
            "uuid": "$gen:uuid",
            "some_field": "$req:parameters.filter.value",
            "some_field_two": "$req:headers.X-User",
            "some_field_three": "$pl:organization.uuid1"
          }
        }
      }
    }
  }
}
```


### Заглушки для описанния
```json
'$req': подстановка значения из запроса. После точки можно подставить любое значение из "request"; 
'$re:': валидация по указанному, после ":", шаблону;
'$gen:': генерация значения, на данный момент возможно генирировать только  "uuid";
'$pl:': подстановка значения из файла placeholers.json
'...': любое значение;
'some_value': при указании точного значения, запрос будет сопоставлять значение из описания и запроса,
на соответсвие;
'$xml:': для ответа в формате xml, указывается в объекте "response.body", после двоеточия нужно указывать файл до xml файла, который будет
использоваться в качестве ответа, на запрос. См. Примере 
```

```json
{
  "name": "example",
  "path": "/example",
  "requests": {
    "get": {
      "request": {
        "headers": {
          "X-User": "..."
        },
        "parameters": {
          "offset": "0",
          "limit": "...",
          "filter": [
            {
              "field": "msisdn",
              "type": "equal",
              "value": "$re:^[0-9]{0,32}$"
            }
          ]
        }
      },
      "response": {
        "status": 200,
        "body": "$xml:{path_to_xml_file}"
      }
    }
  }
}
```



