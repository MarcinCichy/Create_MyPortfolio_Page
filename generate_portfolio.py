import os
import requests
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader

load_dotenv()

GITLAB_TOKEN = os.getenv("GITLAB_TOKEN")  # dodaj w CI/CD Variables, jeśli potrzebne
GITLAB_USERNAME = os.getenv("GITLAB_USERNAME", "MarcinCichy")
MY_NAME = os.getenv("MY_NAME", "Marcin Cichy")
MY_DESCRIPTION = os.getenv("MY_DESCRIPTION", "Marcin Cichy - entuzjasta AI, Pythona, nowocesnych technologii oraz starych komputerów.")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")
SCREENSHOTS_DIR = os.path.join(STATIC_DIR, "screenshots")
IMAGES_DIR = os.path.join(STATIC_DIR, "images")

env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))


def get_user_info(username, token=None):
    """
    Pobiera info o użytkowniku (m.in. avatar_url) z GitLab.
    Jeśli token jest podany, może pobierać prywatne dane,
    ale do publicznych wystarczy brak autoryzacji.
    """
    url = "https://gitlab.com/api/v4/users"
    headers = {}
    if token:
        headers["PRIVATE-TOKEN"] = token
    params = {"username": username}
    r = requests.get(url, headers=headers, params=params)
    r.raise_for_status()
    users = r.json()
    if users:
        return users[0]
    return None


def download_avatar(avatar_url):
    """
    Pobiera avatar i zapisuje go w static/images/avatar.jpg (nadpisuje).
    Zwraca ścieżkę relatywną "static/images/avatar.jpg".
    """
    if not avatar_url:
        return None
    os.makedirs(IMAGES_DIR, exist_ok=True)
    local_path = os.path.join(IMAGES_DIR, "avatar.jpg")
    r = requests.get(avatar_url, stream=True)
    r.raise_for_status()
    with open(local_path, "wb") as f:
        for chunk in r.iter_content(8192):
            f.write(chunk)
    return "static/images/avatar.jpg"


def fetch_gitlab_projects(username, token=None):
    """
    Pobiera listę projektów użytkownika z GitLab.
    Jeśli token jest podany, można pobierać też prywatne proj.
    """
    url = f"https://gitlab.com/api/v4/users/{username}/projects"
    headers = {}
    if token:
        headers["PRIVATE-TOKEN"] = token
    params = {
        "per_page": 100,
        "order_by": "last_activity_at",
        "sort": "desc"
    }
    r = requests.get(url, headers=headers, params=params)
    r.raise_for_status()
    return r.json()


def fetch_repo_tree(project_id, token=None, path="", ref="main"):
    from urllib.parse import quote
    encoded_path = quote(path, safe='')
    url = f"https://gitlab.com/api/v4/projects/{project_id}/repository/tree"
    headers = {}
    if token:
        headers["PRIVATE-TOKEN"] = token
    params = {
        "ref": ref,
        "path": path,
        "per_page": 100
    }
    r = requests.get(url, headers=headers, params=params)
    r.raise_for_status()
    return r.json()


def download_file(project_id, file_path, token=None, ref="main"):
    from urllib.parse import quote
    encoded_path = quote(file_path, safe='')
    url = f"https://gitlab.com/api/v4/projects/{project_id}/repository/files/{encoded_path}/raw"
    headers = {}
    if token:
        headers["PRIVATE-TOKEN"] = token
    params = {"ref": ref}
    r = requests.get(url, headers=headers, params=params)
    r.raise_for_status()
    return r.content


def find_screenshot_paths(project_id, token=None, ref="main"):
    """
    Szuka plików .png/.jpg/.jpeg w możliwych folderach (root, screenshots, images, media).
    Zwraca listę (name, path).
    """
    possible_folders = ["", "screenshots", "Screenshots", "images", "Images", "media"]
    found = []
    for folder in possible_folders:
        try:
            tree = fetch_repo_tree(project_id, token, path=folder, ref=ref)
        except requests.exceptions.HTTPError:
            continue
        for item in tree:
            if item["type"] == "blob":
                fname = item["name"].lower()
                if fname.endswith(".png") or fname.endswith(".jpg") or fname.endswith(".jpeg"):
                    found.append((item["name"], item["path"]))
    return found


def download_first_screenshot(project, token=None):
    """
    Pobiera pierwszy znaleziony screenshot i zwraca lokalną ścieżkę do pliku w static/screenshots.
    """
    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
    project_id = project["id"]
    ref = project.get("default_branch", "main")
    images = find_screenshot_paths(project_id, token=token, ref=ref)
    if not images:
        return None
    first_name, first_path = images[0]
    file_bytes = download_file(project_id, first_path, token=token, ref=ref)
    local_filename = f"{project_id}_{first_name}"
    local_path = os.path.join(SCREENSHOTS_DIR, local_filename)
    with open(local_path, "wb") as f:
        f.write(file_bytes)
    return f"static/screenshots/{local_filename}"


def render_page(template_name, output_filename, **context):
    template = env.get_template(template_name)
    rendered_html = template.render(**context)
    with open(os.path.join(BASE_DIR, output_filename), "w", encoding="utf-8") as f:
        f.write(rendered_html)


def main():
    # 1) Pobierz info o użytkowniku (avatar)
    user_info = get_user_info(GITLAB_USERNAME, GITLAB_TOKEN)
    avatar_url = user_info["avatar_url"] if user_info else None
    avatar_path = download_avatar(avatar_url) if avatar_url else None

    # 2) Pobierz projekty
    projects = fetch_gitlab_projects(GITLAB_USERNAME, GITLAB_TOKEN)

    # 3) Pobierz screenshot (pierwszy) dla każdego projektu
    for p in projects:
        screenshot_path = download_first_screenshot(p, token=GITLAB_TOKEN)
        p["screenshot_path"] = screenshot_path

    # 4) Renderujemy strony
    # index.html (strona główna)
    render_page("index.html", "index.html",
                my_name=MY_NAME,
                my_description=MY_DESCRIPTION,
                avatar_path=avatar_path)

    # programowanie.html
    render_page("programowanie.html", "programowanie.html",
                projects=projects)

    # it.html
    render_page("it.html", "it.html")

    # budownictwo.html
    render_page("budownictwo.html", "budownictwo.html")

    # lasery.html
    render_page("lasery.html", "lasery.html")

    print("Wygenerowano strony w bieżącym katalogu!")


if __name__ == "__main__":
    main()
