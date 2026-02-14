import cloudinary
import cloudinary.uploader
import os

def configure_cloudinary():
    cloudinary.config(
        cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME'),
        api_key = os.environ.get('CLOUDINARY_API_KEY'),
        api_secret = os.environ.get('CLOUDINARY_API_SECRET')
    )

def upload_image(file_path_or_buffer):
    """
    Uploads an image to Cloudinary.
    Returns the secure_url of the uploaded image or None if failed.
    """
    configure_cloudinary()
    try:
        upload_result = cloudinary.uploader.upload(file_path_or_buffer)
        return upload_result.get("secure_url")
    except Exception as e:
        print(f"Cloudinary upload error: {e}")
        return None
