from .models import Post

def get_post_data():
    # BROKEN: This is the N+1 trigger. 
    # It fetches posts, but not the related authors.
    posts = Post.objects.all()
    
    results = []
    for post in posts:
        # Each access of 'post.author' triggers a NEW database hit!
        results.append({
            'title': post.title,
            'author_name': post.author.name 
        })
    return results