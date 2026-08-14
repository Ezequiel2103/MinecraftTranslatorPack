def extract_texts(data):
    texts = []

    def walk(element, path=""):
        if isinstance(element, dict):

            for key, value in element.items():

                new_path = f"{path}.{key}" if path else key

                if isinstance(value, str):
                    texts.append({
                        "path": new_path,
                        "text": value
                    })

                else:
                    walk(value, new_path)

        elif isinstance(element, list):

            for index, value in enumerate(element):
                new_path = f"{path}[{index}]"
                walk(value, new_path)

    walk(data)

    return texts