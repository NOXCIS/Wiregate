import hashlib
import tempfile
import io
import os
import json
import logging
import py7zr
from datetime import datetime

from ...modules.DashboardConfig import DashboardConfig

# Set up logger
logger = logging.getLogger(__name__)



class ArchiveUtils:
    """Handles 7z archive operations with integrity checking"""

    @staticmethod
    def calculate_checksums(files_dict: dict) -> tuple[dict, str]:
        """
        Calculate SHA256 checksums for all files and a final combined checksum
        Returns (file_checksums, combined_checksum)
        """
        try:
            # Calculate individual file checksums
            checksums = {}
            for filename, content in sorted(files_dict.items()):  # Sort for consistent ordering
                if isinstance(content, bytes):
                    checksums[filename] = hashlib.sha256(content).hexdigest()
                elif isinstance(content, str):
                    checksums[filename] = hashlib.sha256(content.encode('utf-8')).hexdigest()

            # Calculate combined checksum
            combined = hashlib.sha256()
            for filename, checksum in sorted(checksums.items()):  # Sort again for consistency
                combined.update(f"{filename}:{checksum}".encode('utf-8'))

            return checksums, combined.hexdigest()

        except Exception as e:
            logger.error(f"Error calculating checksums: {str(e)}")
            raise

    @staticmethod
    def create_archive(files_dict: dict) -> tuple[bytes, dict, str]:
        """
        Create a 7z archive with manifest and checksums
        Returns (archive_bytes, file_checksums, combined_checksum)
        """
        try:
            # Calculate checksums
            logger.debug("Calculating checksums...")
            file_checksums, combined_checksum = ArchiveUtils.calculate_checksums(files_dict)

            # Create manifest
            manifest = {
                'file_checksums': file_checksums,
                'combined_checksum': combined_checksum,
                'timestamp': datetime.now().isoformat(),
                'version': DashboardConfig.GetConfig("Server", "version")[1]
            }

            logger.debug(f"Combined checksum: {combined_checksum}")

            # Add manifest to files
            files_dict['wiregate_manifest.json'] = json.dumps(manifest, indent=2)

            logger.debug("Creating 7z archive in memory...")
            # Create archive in memory
            with tempfile.TemporaryDirectory() as temp_dir:
                # Write files
                for filename, content in files_dict.items():
                    file_path = os.path.join(temp_dir, filename)
                    # Create directories for nested paths
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)

                    if isinstance(content, str):
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                    else:
                        with open(file_path, 'wb') as f:
                            f.write(content)

                # Create 7z archive
                archive_buffer = io.BytesIO()
                with py7zr.SevenZipFile(archive_buffer, 'w') as archive:
                    archive.writeall(temp_dir, arcname='.')

                archive_data = archive_buffer.getvalue()
                logger.debug(f"Archive created successfully, size: {len(archive_data)} bytes")

                return archive_data, file_checksums, combined_checksum

        except Exception as e:
            logger.error(f"Error creating archive: {str(e)}, {type(e)}")
            raise

    @staticmethod
    def verify_archive(archive_data: bytes) -> tuple[bool, str, dict]:
        """
        Verify 7z archive integrity using checksums
        Returns (is_valid, error_message, extracted_files)
        """
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Write archive to temp file
                archive_path = os.path.join(temp_dir, 'archive.7z')
                with open(archive_path, 'wb') as f:
                    f.write(archive_data)

                # Extract archive
                extracted_files = {}
                with py7zr.SevenZipFile(archive_path, 'r') as archive:
                    archive.extractall(temp_dir)

                    # Read all extracted files
                    for root, _, files in os.walk(temp_dir):
                        for filename in files:
                            if filename == 'archive.7z':
                                continue
                            file_path = os.path.join(root, filename)
                            rel_path = os.path.relpath(file_path, temp_dir)
                            with open(file_path, 'rb') as f:
                                extracted_files[rel_path] = f.read()

            # Read manifest
            if 'wiregate_manifest.json' not in extracted_files:
                return False, "No manifest found in archive", {}

            try:
                manifest = json.loads(extracted_files['wiregate_manifest.json'].decode('utf-8'))
            except json.JSONDecodeError as e:
                return False, f"Invalid manifest format: {str(e)}", {}

            if 'file_checksums' not in manifest or 'combined_checksum' not in manifest:
                return False, "Checksums missing from manifest", {}

            # Verify individual file checksums
            logger.debug("Verifying individual file checksums...")
            current_checksums = {}
            for filename, content in extracted_files.items():
                if filename == 'wiregate_manifest.json':
                    continue

                if filename not in manifest['file_checksums']:
                    return False, f"No checksum found for file: {filename}", {}

                calculated_hash = hashlib.sha256(content).hexdigest()
                if calculated_hash != manifest['file_checksums'][filename]:
                    return False, f"Checksum mismatch for file: {filename}", {}
                current_checksums[filename] = calculated_hash

            # Verify combined checksum
            logger.debug("Verifying combined checksum...")
            combined = hashlib.sha256()
            for filename, checksum in sorted(current_checksums.items()):
                combined.update(f"{filename}:{checksum}".encode('utf-8'))

            if combined.hexdigest() != manifest['combined_checksum']:
                return False, "Combined checksum verification failed", {}

            logger.debug("All checksums verified successfully")

            # Remove manifest from extracted files
            del extracted_files['wiregate_manifest.json']
            return True, "", extracted_files

        except Exception as e:
            logger.error(f"Error verifying archive: {str(e)}, {type(e)}")
            return False, f"Error verifying archive: {str(e)}", {}

