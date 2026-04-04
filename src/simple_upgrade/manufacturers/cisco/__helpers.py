

def flash_free_space(show_file_systems, image_size: int = 2000000000):
    """Check if any flash filesystem has enough free space for the image.

    Args:
        show_file_systems: Parsed output from 'show file systems'
        image_size: Image size in bytes (threshold is 2.5x this value)

    Returns:
        True if sufficient space exists on any flash, False otherwise
    """
    file_systems = show_file_systems.get('file_systems', None)
    flash_free_space_threshold = int(image_size * 3.5)
    if flash_free_space_threshold < 1000:
        return {"flash_free_space": 0, "required_free_space": flash_free_space_threshold, "status": False, "message": "Flash free space is less than 1GB"}

    flash_free_space = []
    if file_systems and flash_free_space_threshold:
        for index in file_systems:
            if "flash" in file_systems[index].get('prefixes', ''):
                free_size = file_systems[index]['free_size']
                if free_size and free_size <= flash_free_space_threshold:
                    return {"flash_free_space": free_size, "required_free_space": flash_free_space_threshold, "status": False, "message": "Flash free space is insufficient"}
                else:
                    flash_free_space.append(free_size)
    if flash_free_space:
        flash_free_space.sort(reverse=False)
        return {"flash_free_space": flash_free_space[0], "required_free_space": flash_free_space_threshold, "status": True, "message": "Flash free space is sufficient"}
