# philhopper

Wikipedia articles tend to define the page's subject in the first few sentences. The definition of an entity usually has a higher abstraction level. An interesting side-effect of these two statements is that continually clicking one of the first few links of consequent Wikipedia articles eventually leads to the [Philosophy](https://en.wikipedia.org/wiki/Philosophy) article.

More on this phenomenon can be found [here](https://en.wikipedia.org/wiki/Wikipedia:Getting_to_Philosophy).


**philhopper.py** demonstrates this effect. It:
1. Retrieves 10 Wikipedia articles from the Wikipedia API (randomly)
2. For each article:
    2.1 Extracts the first hyperlink (that is not inside parentheses)
    2.2 Clicks the link, retrieves the article, and then goes to step 2.1. Do this recursively until a cycle is detected, the Philosophy article is reached, or an HTML parsing error is called (rare).

**Note**: The script will continually try hopping to the target article. To cancel it, press "Ctrl + C".


**example_output.txt** contains the output of the script on ten random articles.