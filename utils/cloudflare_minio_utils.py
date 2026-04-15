from minio import Minio
from minio.error import S3Error
from utils.common_import_utils import print_log
from PIL import Image
import mimetypes
from io import BytesIO
import requests
import uuid
import traceback
import os
from datetime import datetime

account_id = os.getenv("CLOUDFLARE_R2_ACCOUNT_ID", "69b7a22f88758a961915a57a9dc476c4")
api_token = os.getenv("CLOUDFLARE_API_TOKEN", "")
email = os.getenv("CLOUDFLARE_EMAIL", "")
api_key = os.getenv("CLOUDFLARE_API_KEY", "")
ACCESS_KEY = os.getenv("CLOUDFLARE_R2_ACCESS_KEY", "")
SECRET_KEY = os.getenv("CLOUDFLARE_R2_SECRET_KEY", "")
ENDPOINT_URL = f"https://{account_id}.r2.cloudflarestorage.com"
BUCKET_NAME = "agency"
DOMAIN = os.getenv("CLOUDFLARE_R2_PUBLIC_DOMAIN", "media.bablumia.site")


client = Minio(
    endpoint=f"{account_id}.r2.cloudflarestorage.com",
    access_key=ACCESS_KEY,
    secret_key=SECRET_KEY,
    secure=True
)
class CompressedImageFile:
    def __init__(self, image_data, name):
        self.image_data = image_data
        self.name = name
        self._position = 0

    def read(self, size=None):
        if size is None:
            # Read all remaining data
            data = self.image_data.getvalue()[self._position:]
            self._position = len(self.image_data.getvalue())
            return data
        else:
            # Read specified amount of data
            data = self.image_data.getvalue()[self._position:self._position + size]
            self._position += len(data)
            return data

    def seek(self, offset, whence=0):
        if whence == 0:  # Beginning of file
            self._position = offset
        elif whence == 1:  # Current position
            self._position += offset
        elif whence == 2:  # End of file
            self._position = len(self.image_data.getvalue()) + offset
        return self._position


def upload_image_from_url_to_r2(image_url: str, quality=None, width=None, height=None):
    try:
        # Step 1: Download the image from the URL
        response = requests.get(image_url)
        response.raise_for_status()

        # Step 2: Check the image size in KB
        image_size_kb = len(response.content) / 1024  # Convert to KB
        if image_size_kb <= 100:
            print("Image size is less than or equal to 100 KB, skipping upload.")
            return None

        # Step 3: Load the image using PIL
        image = Image.open(BytesIO(response.content))
        file_name = image_url.split("/")[-1]

        # Step 4: Compress and resize if necessary
        if width and height:
            compressed_image = compress_and_remove_metadata(image, quality, width, height)
        else:
            compressed_image = compress_and_remove_metadata(image, quality)

        # Step 5: Prepare for upload
        length = compressed_image.getbuffer().nbytes
        content_type = 'image/webp'
        object_name = f"{file_name.split('.')[0]}_{width or 'original'}x{height or 'original'}.webp"

        # Step 6: Upload to R2
        client.put_object(
            bucket_name=BUCKET_NAME,
            object_name=object_name,
            data=compressed_image,
            length=length,
            content_type=content_type
        )

        # Return the uploaded image URL
        return f"{DOMAIN}/{object_name}"
    
    except requests.RequestException as e:
        print(f"Failed to download image: {e}")
        return None
    except S3Error as e:
        print(f"Failed to upload image to R2: {e}")
        return None

def upload_file_to_r2(file, quality=None, width=None, height=None):
    try:
        if width and height:
            # Check if it's a CompressedImageFile object
            if isinstance(file, CompressedImageFile):
                # For CompressedImageFile, the data is already compressed
                data = file.image_data
                length = data.getbuffer().nbytes
                content_type = 'image/webp'
                object_name = f"{file.name.split('.')[0]}_{width}x{height}.webp"
            else:
                # For regular file objects
                image = Image.open(file.file)
                compressed_image = compress_and_remove_metadata(image, quality, width, height)
                data = compressed_image
                length = compressed_image.getbuffer().nbytes
                content_type = 'image/webp'
                object_name = f"{file.name.split('.')[0]}_{width}x{height}.webp"
        else:
            # Check if it's a CompressedImageFile object
            if isinstance(file, CompressedImageFile):
                data = file.image_data
                length = data.getbuffer().nbytes
                content_type = 'image/webp'
                object_name = file.name
            else:
                # For regular file objects
                data = file.file
                length = file.size
                content_type, _ = mimetypes.guess_type(file.name)
                content_type = content_type or 'application/octet-stream'
                object_name = file.name

        client.put_object(
            bucket_name=BUCKET_NAME,
            object_name=object_name,
            data=data,
            length=length,
            content_type=content_type
        )

        return f"{DOMAIN}/{object_name}"
    except S3Error as e:
        print_log(f"Failed to upload file to R2: {e}")
        raise e

def compress_and_remove_metadata(image, quality=None, width=None, height=None):
    # Convert to RGB to ensure compatibility
    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")

    # Resize the image if width and height are provided
    if width and height:
        width, height = int(width), int(height)
        image = image.resize((width, height), Image.LANCZOS)
        quality = quality or 85
    else:
        quality = quality or 75

    # Save image to BytesIO without metadata (EXIF) and optimized compression
    output = BytesIO()
    image.save(output, format='webp', quality=quality, optimize=True, method=6)
    output.seek(0)

    return output

def compress_and_upload_to_r2(image, file_name, quality=100,width=None, height=None):
    try:
        # Compress the image
        compressed_image = compress_and_remove_metadata(image, quality=quality, width=width, height=height)
        
        # Generate unique filename with timestamp and UUID
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        short_uuid = str(uuid.uuid4().hex)[:5]
        unique_file_name = f"{file_name}_{timestamp}_{short_uuid}.webp"
        
        # Create a file-like object that upload_file_to_r2 can use
        file_obj = CompressedImageFile(compressed_image, unique_file_name)
        
        # Use the existing upload_file_to_r2 function
        return upload_file_to_r2(file_obj,quality=quality, width=width, height=height)
    except Exception as e:
        print_log(f"Failed to compress and upload image to R2: {e}", "compress_and_upload_to_r2")
        traceback.print_exc()
        return None
    
from urllib.parse import unquote

def delete_image_from_r2(file_url):
    try:
        if not file_url.startswith(DOMAIN):
            raise ValueError("Invalid file URL. It does not match expected domain.")

        # Decode URL and extract object name
        encoded_object_name = file_url.replace(f"{DOMAIN}/", "")
        object_name = unquote(encoded_object_name)  # ✅ decode %20 to space

        print_log(f"Object name to delete: {object_name}", "delete_image_from_r2")

        client.remove_object(bucket_name=BUCKET_NAME, object_name=object_name)

        print_log(f"Successfully deleted image from R2: {object_name}", "delete_image_from_r2")
        return True

    except S3Error as e:
        print_log(f"Failed to delete image from R2: {e}", "delete_image_from_r2")
        return False
    except Exception as e:
        print_log(f"Unexpected error deleting image from R2: {e}", "delete_image_from_r2")
        return False
