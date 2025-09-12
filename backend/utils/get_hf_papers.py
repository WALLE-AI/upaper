import json
from typing import List

from bs4 import BeautifulSoup
import requests


def get_hugging_face_top_daily_paper() -> List:
    """
    This is a tool that returns the most upvoted paper on Hugging Face daily papers.
    It returns the title of the paper
    """
    try:
      url = "https://huggingface.co/papers"
      response = requests.get(url)
      response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
      soup = BeautifulSoup(response.content, "html.parser")

      # Extract the title element from the JSON-like data in the "data-props" attribute
      containers = soup.find_all('div', class_='SVELTE_HYDRATER contents')
      top_paper_list = []
      top_paper = ""

      for container in containers:
          data_props = container.get('data-props', '')
          if data_props:
              try:
                  # Parse the JSON-like string
                  json_data = json.loads(data_props.replace('&quot;', '"'))
                  if 'dailyPapers' in json_data:
                    #   top_paper = json_data['dailyPapers'][0]['title']
                      for top_paper in json_data['dailyPapers']:
                          top_paper_list.append(top_paper['paper'])
              except json.JSONDecodeError:
                  continue
      print("top paper list:",top_paper_list)
    #   with open("top_daily_paper_list.jsonl", "w", encoding="utf-8") as f:
    #         f.write(json.dumps(top_paper_list,ensure_ascii=False,indent=4))
      return top_paper_list
    except requests.exceptions.RequestException as e:
      print(f"Error occurred while fetching the HTML: {e}")
      return None
    
if __name__ == "__main__":
    get_hugging_face_top_daily_paper()  