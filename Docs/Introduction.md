## **Getting Started**

### Target URLs

When first creating your configuration file, the first thing you'll need to do is specify target URLs. Think of these as the initial pages where the scraper should start. For example, if you're scraping information about books from [All products | Books to Scrape - Sandbox](https://books.toscrape.com/index.html), your target URL would be the main page of the website. This choice becomes important when we delve into the **page navigator**.

Here is a basic example of how to define target URLs:

```json
{
  "target_urls": [
    {
      "url": "https://books.toscrape.com/"
    }
  ]
}
```

The `target_urls` field is a list of the pages you want your scraper to initially visit. You can also provide custom options for each target URL. These options include whether to render the pages and whether the scraper should scrape only the sub pages or both the target URL and its sub pages.

Here's an example with additional options:

```json
{
"target_urls": [
    {
      "url": "https://books.toscrape.com/",
      "options": {
        "only_scrape_sub_pages": true,
        "render_pages": false
      }
    }
  ]
}
```

In this example, the `only_scrape_sub_pages` option is set to `true`, indicating that the scraper won't scrape the target URL (main page), but it will scrape its sub pages (i.e., individual book/product pages). The `render_pages` option determines whether the pages should be rendered; set it to `true` to render pages, or `false` to skip rendering.

> **Note:** If no options are specified, the default behavior is as follows:
>
> - `only_scrape_sub_pages`: True
> - `render_pages`: False

To summarize:

- The `url` field specifies the page to start scraping.
- The `options` field is optional and allows you to customize the scraping behavior.

Using these configurations, you can guide the scraper to the right starting point and control its behavior for efficient data collection.

Remember that these are just the first steps in configuring your web scraper. Let's explore more aspects of configuration in the following sections.

## Elements

In your configuration file, the elements are what the scraper will be extracting from different pages. All the elements are stored in a list of different element objects.

**When it comes to selecting elements, you have four options:**

> * [**CSS selectors**](#CSS Selectors)
> * [**Tags and attributes**](#Tags and Attributes Selector)
> * [**Search hierarchy**](#Search Hierarchy Selector)
> * [**XPath**](#XPath Selector)

When defining elements, you first need to create a list called **elements**.

```json
{
  "target_urls": [
    {
      "url": "https://books.toscrape.com/"
    }
  ],
  "elements": []
}
```

## CSS Selectors

Now that you have a list of elements, it's time to create your first element.

```json
"elements": [
    {
      "css_selector": ".product_main p.price_color"
    }
  ]
```

Creating an element that targets elements with CSS selectors is quite simple. Just specify it as a **css_selector**, followed by the CSS pattern. In this example, this element is extracting an HTML element that holds information about the main product's price.

Here's what that HTML looks like:

```html
<div class="col-sm-6 product_main"> 
    <p class="price_color">£50.10</p>
</div>
```

Using the CSS selector **.product_main p.price_color** will give us the element:

```html
<p class="price_color">£50.10</p>
```

This is exactly what we want, as it's the element that holds the product's price.

## Tags and Attributes Selector

If CSS selectors won't suffice for your use case, you can try using tags and attributes. The tag is the HTML tag of the element you want, and the attributes are a list of attributes to look for.

```json
"elements": [
    {
      "tag": "p",
      "attributes":[
          {
              "name": "attr_name",
              "value": "attr_value"
          }
      ]
    }
  ]
```

You might be wondering, what if I want to get an element that has multiple attributes? In that case, you have two options with this approach.

```json
"elements": [
    {
      "tag": "p",
      "attributes":[
          {
              "name": "attr_name_one",
              "value": "attr_value_one"
          },
          {
              "name": "attr_name_two",
              "value": "attr_value_two"
          }
      ]
    }
  ]
```

Here, you can specify more than one attribute name and value pair. Additionally, if the attribute names are the same, you can use a list to specify different values.

```json
"elements": [
    {
      "tag": "p",
      "attributes":[
          {
              "name": "attr_name_one",
              "value": ["attr_value_one", "attr_value_two"]
          }
        
      ]
    }
  ]
```

> **Note**: The list for mutliple attribue values is options and can be written like this
>
> ```json
> "name": "attr_name_one",
> "value": "attr_value_one attr_value_two"
> ```

## **Search Hierarchy Selector**

The "Search Hierarchy Selector" is your powerful ally when it comes to extracting specific elements amidst a sea of similar content. Consider this scenario: you're on a product page, aiming to extract the product price. However, lurking below lies a challenge – a section showcasing recommended products. Your traditional approach to capturing the product price might inadvertently fetch prices of both the main product and the recommendations. This is precisely where the "Search Hierarchy Selector" comes to the rescue. It enables you to elegantly filter out the extraneous elements and zero in on your primary target – the main product price.

### How It Works

The "Search Hierarchy Selector" employs a step-by-step methodology. It meticulously seeks out elements that correspond to each attribute, respecting the order you've set. This systematic exploration allows you to gracefully navigate through nested elements, pinpointing your intended prize.

### Configuration Example

Let's delve into configuring the **"Search Hierarchy Selector"** within your JSON configuration file:

```json
"elements": [
  {
    "search_hierarchy": [
      {
        "name": "class",
	    "value": "main-product"
      },
      {
        "name": "class",
        "value": "product-details"
      },
      {
        "name": "class",
        "value": "price"
      }
    ]
  }
]
```

### Explanation of Example

Consider a scenario where your target product price is nestled within the following hierarchy: `<div class="main-product"><div class="product-details"><div class="price">...</div></div></div>`. The "Search Hierarchy Selector" systematically sifts through elements that possess the specified attributes: first, "class" with the value "main-product" then, "class" with the value "product-details", finally "class" with the value "price."

This mechanism empowers you to precisely target elements that adhere to a specific nesting pattern, ensuring that you exclusively retrieve the desired data.

### HTML Example

Let's visualize the HTML layout that you might encounter:

```html
<div class="main-product">
    <div class="product-details">
      <div class="price">
        <!-- This is your target: the product price -->
      </div>
    </div>
</div>

<!-- Some other html -->

<div class="recommend-products">
    <div class="product-details">
      <div class="price">
        <!-- Avoid this: extraneous price -->
      </div>
    </div>
    <div class="product-details">
      <div class="price">
        <!-- Avoid this: extraneous price -->
      </div>
    </div>
</div>
```

Within this HTML snippet, the `Search Hierarchy Selector` deftly homes in on the innermost `<div>` element with the class "price" – precisely where your coveted product price is located.

### Use Cases

The `Search Hierarchy Selector` truly shines in intricate webpage landscapes. When your desired data is concealed within complex nesting patterns, this tool acts as a beacon, expertly guiding you toward your intended bounty.

### Benefits

- **Flexibility**: Seamlessly traverse intricate elements to reach your coveted data.
- **Intuitive**: Choreograph a sequence of attributes to mirror your desired exploration path.
- **Efficiency**: Extract data from convoluted structures without crafting convoluted XPath expressions.

The "Search Hierarchy Selector" stands as your versatile companion, augmenting your arsenal of element selection techniques and empowering you to masterfully conquer a multitude of web scraping challenges.

## **XPath Selector**



> **NOTE:** XPath selector is not supported yet, but will be soon!
