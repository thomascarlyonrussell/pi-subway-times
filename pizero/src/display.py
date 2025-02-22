
# # Function to clear all text boxes
# def clear_text_boxes():
#     # matrixportal.remove_all_text()
#     for i in range(12):  # Assuming there are 12 text boxes
#         try: matrixportal.set_text("", i)
#         except: pass

# def build_trip_text(trip, column, index):
#     if column == 0:
#         return str(index)
#     elif column == 1:
#         return trip["line"]
#     elif column == 2:
#         return trip["direction"]
#     elif column == 3:
#         return str(trip["minutes_until_arrival"])

# # Function to update the countdown timer
# def update_countdown_timer(start_time, refresh_time_delay):
#     elapsed_time = time.monotonic() - start_time
#     total_pixels = 32  # Assuming the width of the display is 32 pixels
#     pixels_on = int(((refresh_time_delay - elapsed_time) / refresh_time_delay) * total_pixels)
#     countdown_text = "i" * pixels_on + " " * (total_pixels - pixels_on)
#     matrixportal.set_text(countdown_text, 12)
#     return

# def start_grid(trip_json):
#     for j in range(4):
#         if len(trip_json) > 0:
#             # Display the first trip
#             matrixportal.set_text(build_trip_text(trip_json[0], j, 1), j)
#             matrixportal.set_text_color(int(trip_json[0].get('route_color', 'FFFFFF'), 16) if j != 0 else 0xFFFFFF, j)
#         if len(trip_json) > 1:
#             # Display the second trip
#             matrixportal.set_text(build_trip_text(trip_json[1], j, 2), 4 + j)
#             matrixportal.set_text_color(int(trip_json[1].get('route_color', 'FFFFFF'), 16) if j != 0 else 0xFFFFFF, 4 + j)
#     return

# def update_grid(trip_json, start_index=2):
#     trip_size = len(trip_json)
#     for i in range(start_index, trip_size):
#         for j in range(4):
#             if trip_size > 0:
#                 # Display the first trip
#                 matrixportal.set_text(build_trip_text(trip_json[0], j, 1), j)
#                 matrixportal.set_text_color(int(trip_json[0].get('route_color', 'FFFFFF'), 16) if j != 0 else 0xFFFFFF, j)
#             if trip_size > 1:
#                 # Display the second trip
#                 matrixportal.set_text(build_trip_text(trip_json[1], j, 2), 4 + j)
#                 matrixportal.set_text_color(int(trip_json[1].get('route_color', 'FFFFFF'), 16) if j != 0 else 0xFFFFFF, 4 + j)
#             if trip_size > i:
#                 # Display the third trip
#                 matrixportal.set_text(build_trip_text(trip_json[i], j, i+1), 8 + j)
#                 matrixportal.set_text_color(int(trip_json[i].get('route_color', 'FFFFFF'), 16) if j != 0 else 0xFFFFFF, 8 + j)
#         update_countdown_timer(start_time, REFRESH_TIME_DELAY)
#         time.sleep(TIME_DELAY)
#     return
