import os
import requests
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader

load_dotenv()

GITLAB_TOKEN = os.getenv("GITLAB_TOKEN")
GITLAB_USERNAME = os.getenv("GITLAB_USERNAME", "moj_login_gitlab")
MY_NAME = os.getenv("MY_NAME", "Jan Kowalski")
MY_DESCRIPTION = os.getenv("MY_DESCRIPTION", "Programista, miłośnik technologii i laserów")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")
SCREENSHOTS_DIR = os.path.join(STATIC_DIR, "screenshots")
IMAGES_DIR = os.path.join(STATIC_DIR, "images")

env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))


def get_user_info(username, token):
    """Pobiera info o użytkowniku (m.in. avatar_url)."""
    url = "https://gitlab.com/api/v4/users"
    headers = {"PRIVATE-TOKEN": token}
    params = {"username": username}
    r = requests.get(url, headers=headers, params=params)
    r.raise_for_status()
    users = r.json()
    if users:
        return users[0]
    return None


def download_avatar(avatar_url):
    """Pobiera avatar i zapisuje go w static/images/avatar.jpg (nadpisuje)."""
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


def fetch_gitlab_projects(username, token):
    """Pobiera listę projektów z GitLab."""
    url = f"https://gitlab.com/api/v4/users/{username}/projects"
    headers = {"PRIVATE-TOKEN": token}
    params = {
        "per_page": 100,
        "order_by": "last_activity_at",
        "sort": "desc"
    }
    r = requests.get(url, headers=headers, params=params)
    r.raise_for_status()
    return r.json()


def fetch_repo_tree(project_id, token, path="", ref="main"):
    from urllib.parse import quote
    encoded_path = quote(path, safe='')
    url = f"https://gitlab.com/api/v4/projects/{project_id}/repository/tree"
    headers = {"PRIVATE-TOKEN": token}
    params = {
        "ref": ref,
        "path": path,
        "per_page": 100
    }
    r = requests.get(url, headers=headers, params=params)
    r.raise_for_status()
    return r.json()


def download_file(project_id, token, file_path, ref="main"):
    from urllib.parse import quote
    encoded_path = quote(file_path, safe='')
    url = f"https://gitlab.com/api/v4/projects/{project_id}/repository/files/{encoded_path}/raw"
    headers = {"PRIVATE-TOKEN": token}
    params = {"ref": ref}
    r = requests.get(url, headers=headers, params=params)
    r.raise_for_status()
    return r.content


def find_screenshot_paths(project_id, token, ref="main"):
    """
    Szuka w głównym katalogu i w 'screenshots', 'Screenshots',
    'images', 'Images', 'media' - plików .png/.jpg/.jpeg.
    Zwraca listę (name, path w repo). Tu można pobrać tylko pierwszy,
    albo wszystkie do listy.
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


def download_first_screenshot(project, token):
    """
    Pobiera pierwszy znaleziony screenshot i zwraca lokalną ścieżkę.
    """
    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
    project_id = project["id"]
    ref = project.get("default_branch", "main")
    images = find_screenshot_paths(project_id, token, ref=ref)
    if not images:
        return None
    # Bierzemy pierwszy
    first_name, first_path = images[0]
    file_bytes = download_file(project_id, token, first_path, ref=ref)
    local_filename = f"{project_id}_{first_name}"
    local_path = os.path.join(SCREENSHOTS_DIR, local_filename)
    with open(local_path, "wb") as f:
        f.write(file_bytes)
    return f"static/screenshots/{local_filename}"


def main():
    if not GITLAB_TOKEN:
        print("Brak GITLAB_TOKEN w .env")
        return

    # 1) Avatar
    user_info = get_user_info(GITLAB_USERNAME, GITLAB_TOKEN)
    avatar_url = user_info["avatar_url"] if user_info else None
    avatar_path = download_avatar(avatar_url) if avatar_url else None

    # 2) Projekty
    projects = fetch_gitlab_projects(GITLAB_USERNAME, GITLAB_TOKEN)

    # 3) Dla każdego projektu pobierz screenshot (pierwszy znaleziony)
    for p in projects:
        sc = download_first_screenshot(p, GITLAB_TOKEN)
        p["screenshot_path"] = sc

    # 4) Renderuj podstrony
    #   a) Strona główna (index.html)
    index_template = env.get_template("index.html")
    index_html = index_template.render(
        my_name=MY_NAME,
        my_description=MY_DESCRIPTION,
        avatar_path=avatar_path,
    )
    with open(os.path.join(BASE_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)

    #   b) Programowanie (programowanie.html)
    prog_template = env.get_template("programowanie.html")
    prog_html = prog_template.render(
        projects=projects
        # Możesz też przekazać my_name, my_description, itp. –
        # jeśli chcesz użyć w danej podstronie
    )
    with open(os.path.join(BASE_DIR, "programowanie.html"), "w", encoding="utf-8") as f:
        f.write(prog_html)

    #   c) IT (it.html)
    it_template = env.get_template("it.html")
    it_html = it_template.render()
    with open(os.path.join(BASE_DIR, "it.html"), "w", encoding="utf-8") as f:
        f.write(it_html)

    #   d) Budownictwo (budownictwo.html)
    bud_template = env.get_template("budownictwo.html")
    bud_html = bud_template.render()
    with open(os.path.join(BASE_DIR, "budownictwo.html"), "w", encoding="utf-8") as f:
        f.write(bud_html)

    #   e) Lasery (lasery.html)
    lasery_template = env.get_template("lasery.html")
    lasery_html = lasery_template.render()
    with open(os.path.join(BASE_DIR, "lasery.html"), "w", encoding="utf-8") as f:
        f.write(lasery_html)

    print("Wygenerowano wszystkie podstrony portfolio.")


if __name__ == "__main__":
    main()
