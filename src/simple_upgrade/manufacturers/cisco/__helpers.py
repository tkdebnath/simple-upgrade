

def flash_free_space(show_file_systems, image_size: int = 2000000000):

    file_systems = show_file_systems.get('file_systems', None)
    flash_free_space_threshold = int(image_size * 2.5)

    if file_systems and flash_free_space_threshold:
        for index in file_systems:
            if "flash" in file_systems[index].get('prefixes', ''):
                free_size = file_systems[index].get('free_size', '')
                if free_size and free_size < flash_free_space_threshold:
                    return
        return True