import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the GitHub token and username from environment variables
GITLAB_TOKEN = os.getenv("GITLAB_TOKEN")
GITLAB_USERNAME = os.getenv("GITLAB_USERNAME")

# Get other environment variables
MY_NAME = os.getenv("MY_NAME")
MY_DESCRIPTION = os.getenv("MY_DESCRIPTION")

# Define template HTML
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8"/>
    <title>Portfolio - {my_name}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f3f3f3;
        }}
        h1, h2 {{
            text-align: center;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: #fff;
            padding: 20px;
            border-radius: 8px;
        }}
        .projects {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 20px;
        }}
        .project-card {{
            background-color: #fafafa;
            border: 1px solid #ddd;
            border-radius: 5px;
            flex: 1 1 300px;
            padding: 15px;
            box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
        }}
        .project-card h3 {{
            margin-top: 0;
        }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            font-size: 0.9em;
            color: #666;
        }}
        .about-me {{
            text-align: center;
            margin: 20px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Portfolio - {my_name}</h1>
        <div class="about-me">
            <p><strong>O mnie:</strong> {my_description}</p>
        </div>
        <hr />
        <h2>Moje projekty na GitLab</h2>
        <div class="projects">
        {projects_html}
        </div>
        <div class="footer">
            <p>Strona wygenerowana automatycznie przez Python + GitLab API.</p>
        </div>
    </div>
</body>
</html>
"""

PROJECT_TEMPLATE = """
<div class="project-card">
    <h3>{name}</h3>
    <p><strong>Opis:</strong> {description}</p>
    <p><strong>Repo:</strong> <a href="{web_url}" target="_blank">{web_url}</a></p>
</div>
"""


def fetch_gitlab_projects(username, private_token):
    """
    Pobiera listę projektów (repozytoriów) użytkownika z GitLab,
    używając endpointu https://gitlab.com/api/v4/users/<username>/projects
    """
    url = f"https://gitlab.com/api/v4/users/{username}/projects"
    headers = {
        "PRIVATE-TOKEN": private_token
    }
    params = {
        "per_page": 100,  # Jeśli masz bardzo dużo projektów, może być potrzebna paginacja
        "order_by": "last_activity_at",
        "sort": "desc"
    }

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()  # jeśli zwróci błąd 4XX lub 5XX, rzuć wyjątek
    projects = response.json()

    return projects


def generate_portfolio_html(my_name, my_description, projects):
    """
    Generuje końcowy HTML, wypełniając szablon danymi o projektach i podstawowymi informacjami o autorze.
    """
    project_cards = []
    for p in projects:
        project_name = p["name"]
        project_desc = p.get("description", "Brak opisu...")
        project_url = p["web_url"]
        project_cards.append(
            PROJECT_TEMPLATE.format(name=project_name, description=project_desc, web_url=project_url)
        )

    projects_html = "\n".join(project_cards)

    # Wypełniamy główny szablon
    final_html = HTML_TEMPLATE.format(
        my_name=my_name,
        my_description=my_description,
        projects_html=projects_html
    )
    return final_html


def main():
    # Sprawdzamy, czy token i username w ogóle istnieją
    if not GITLAB_TOKEN:
        print("Brak tokena GitLab. Upewnij się, że masz plik .env i zmienną GITLAB_TOKEN.")
        return

    # Pobieramy projekty
    projects = fetch_gitlab_projects(GITLAB_USERNAME, GITLAB_TOKEN)

    # Generujemy gotowy HTML
    html_content = generate_portfolio_html(MY_NAME, MY_DESCRIPTION, projects)

    # Zapisujemy do pliku
    output_file = "portfolio.html"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"Plik {output_file} został wygenerowany pomyślnie!")


if __name__ == "__main__":
    main()