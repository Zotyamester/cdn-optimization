import pulp as lp
from plot import basemap_plot_network
from sample import network
from solver import get_optimal_topology_for_multiple_tracks
from traffic import generate_video_conference_traffic
import glob
import numpy as np
import imageio
import os

def experiment_with_bitrate_variation(image_path, lower_bound, upper_bound, step):
    for bitrate in range(lower_bound, upper_bound + step, step):
        tracks = generate_video_conference_traffic(
            ["Budapest", "Aalborg", "eu-west-3", "eu-west-2", "eu-north-1", "us-west-1", "us-west-2", "eu-central-1"], bitrate=bitrate)

        status, used_links_per_track = get_optimal_topology_for_multiple_tracks(
            network, tracks)
        
        if status != lp.LpStatusOptimal:
            print(f"No optimal solution found when restricting bitrate to {bitrate} ms. Skipping...")
            continue

        track_to_color = {track_id: color for track_id,
                          color in zip(tracks.keys(), COLORS)}

        basemap_plot_network(network, tracks, track_to_color,
                             used_links_per_track, f"{image_path}/img{bitrate:02d}.png")

def make_video(image_path, movie_filename, fps):
    # sorting filenames in order
    filenames = glob.glob(f"{image_path}/img*.png")
    filenames_sort_indices = np.argsort([int(os.path.basename(filename).split(".")[0][3:]) for filename in filenames])
    filenames = [filenames[i] for i in filenames_sort_indices]

    # make movie
    with imageio.get_writer(movie_filename, mode="I", fps=fps) as writer:
        for filename in filenames:
            image = imageio.imread(filename)
            writer.append_data(image)

if __name__ == "__main__":
    COLORS = ["red", "blue", "green", "yellow",
              "purple", "orange", "pink", "brown"]

    experiment_with_bitrate_variation("plots/", 10, 100, 10)
    #experiment_with_bitrate_variation("plots/", 100, 200, 40)
    make_video("plots/", "video.mp4", 2)
