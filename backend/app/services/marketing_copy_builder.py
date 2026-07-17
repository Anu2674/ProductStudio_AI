def build_marketing_content(product_name: str, category: str, key_features: list[str]) -> dict:
    title = f"{product_name} - Premium {category.title()}"

    feature_clause = f", featuring {', '.join(key_features)}," if key_features else ""
    description = (
        f"Introducing the {product_name}, a premium {category} designed for everyday use"
        f"{feature_clause} crafted with quality and durability in mind."
    )

    bullet_points = [f"High-quality {category}"]
    bullet_points.extend(f"Features {feature}" for feature in key_features)
    if not key_features:
        bullet_points.append("Designed for durability and everyday use")

    social_caption = f"Meet the {product_name} - shop now and elevate your {category} game."

    seo_keywords = [product_name.lower(), category.lower()]
    seo_keywords.extend(feature.lower() for feature in key_features)

    return {
        "title": title,
        "description": description,
        "bullet_points": bullet_points,
        "social_caption": social_caption,
        "seo_keywords": seo_keywords,
    }
