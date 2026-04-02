

def flash_free_space(show_file_systems, image_size: int = 2000000000):
    """Check if any flash filesystem has enough free space for the image.

    Args:
        show_file_systems: Parsed output from 'show file systems'
        image_size: Image size in bytes (threshold is 2.5x this value)

    Returns:
        True if sufficient space exists on any flash, False otherwise
    """
    file_systems = show_file_systems.get('file_systems', None)
    flash_free_space_threshold = int(image_size * 2.5)

    if file_systems and flash_free_space_threshold:
        for index in file_systems:
            if "flash" in file_systems[index].get('prefixes', ''):
                free_size = file_systems[index].get('free_size', 0)
                if free_size and free_size >= flash_free_space_threshold:
                    return True  # Found a flash with enough space
        return False  # No flash had enough space
    return False