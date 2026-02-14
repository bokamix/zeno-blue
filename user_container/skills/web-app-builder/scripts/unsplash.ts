#!/usr/bin/env bun
/**
 * Unsplash Image Downloader
 *
 * Downloads images from Unsplash based on search query.
 *
 * Usage:
 *   bun run /app/user_container/skills/web-app-builder/scripts/unsplash.ts <query> [options]
 *
 * Examples:
 *   bun run unsplash.ts "office workspace" --count 3
 *   bun run unsplash.ts "nature landscape" --output /workspace/my-app/images --orientation landscape
 *   bun run unsplash.ts "portrait woman" --orientation portrait --count 1
 *
 * Options:
 *   --count, -n       Number of images to download (default: 1, max: 10)
 *   --output, -o      Output directory (default: current directory)
 *   --orientation     Image orientation: landscape, portrait, squarish (default: any)
 *   --size            Image size: raw, full, regular, small, thumb (default: regular)
 */

import { parseArgs } from "util";
import { mkdir } from "fs/promises";
import { join } from "path";

const UNSPLASH_ACCESS_KEY = process.env.UNSPLASH_ACCESS_KEY || "";

interface UnsplashPhoto {
  id: string;
  slug: string;
  description: string | null;
  alt_description: string | null;
  urls: {
    raw: string;
    full: string;
    regular: string;
    small: string;
    thumb: string;
  };
  links: {
    download_location: string;
  };
  user: {
    name: string;
    username: string;
    links: {
      html: string;
    };
  };
}

interface SearchResponse {
  total: number;
  total_pages: number;
  results: UnsplashPhoto[];
}

async function searchPhotos(
  query: string,
  options: {
    count?: number;
    orientation?: string;
  } = {}
): Promise<UnsplashPhoto[]> {
  const params = new URLSearchParams({
    query,
    per_page: String(Math.min(options.count || 1, 30)),
  });

  if (options.orientation) {
    params.set("orientation", options.orientation);
  }

  const response = await fetch(
    `https://api.unsplash.com/search/photos?${params}`,
    {
      headers: {
        Authorization: `Client-ID 5JyWPOkT-TsRoOTFNqTh-zA7IOfToIOTKwFF7--8N8U`,
      },
    }
  );

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Unsplash API error: ${response.status} - ${error}`);
  }

  const data: SearchResponse = await response.json();
  return data.results;
}

async function triggerDownload(photo: UnsplashPhoto): Promise<void> {
  // Trigger download event for Unsplash attribution tracking
  await fetch(photo.links.download_location, {
    headers: {
      Authorization: `Client-ID 5JyWPOkT-TsRoOTFNqTh-zA7IOfToIOTKwFF7--8N8U`,
    },
  });
}

async function downloadImage(
  photo: UnsplashPhoto,
  outputDir: string,
  size: string = "regular"
): Promise<string> {
  const url = photo.urls[size as keyof typeof photo.urls] || photo.urls.regular;

  // Trigger download tracking
  await triggerDownload(photo);

  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to download image: ${response.status}`);
  }

  const buffer = await response.arrayBuffer();

  // Generate filename from slug or id
  const filename = `${photo.slug || photo.id}.jpg`;
  const filepath = join(outputDir, filename);

  await Bun.write(filepath, buffer);

  return filepath;
}

function printAttribution(photo: UnsplashPhoto): void {
  console.log(`  Photo by ${photo.user.name} (@${photo.user.username})`);
  console.log(`  ${photo.user.links.html}?utm_source=your_app&utm_medium=referral`);
  if (photo.alt_description) {
    console.log(`  Alt: ${photo.alt_description}`);
  }
}

function printUsage(): void {
  console.log(`
Unsplash Image Downloader

Usage:
  bun run unsplash.ts <query> [options]

Arguments:
  query              Search query (e.g., "office workspace", "nature")

Options:
  --count, -n        Number of images to download (default: 1, max: 10)
  --output, -o       Output directory (default: current directory)
  --orientation      Image orientation: landscape, portrait, squarish
  --size             Image size: raw, full, regular, small, thumb (default: regular)
  --help, -h         Show this help message

Examples:
  bun run unsplash.ts "modern office"
  bun run unsplash.ts "nature landscape" --count 3 --orientation landscape
  bun run unsplash.ts "coffee" --output ./images --size small

Environment:
  UNSPLASH_ACCESS_KEY   Your Unsplash API access key (required)
`);
}

async function main() {
  const { values, positionals } = parseArgs({
    args: Bun.argv.slice(2),
    options: {
      count: { type: "string", short: "n", default: "1" },
      output: { type: "string", short: "o", default: "." },
      orientation: { type: "string" },
      size: { type: "string", default: "regular" },
      help: { type: "boolean", short: "h", default: false },
    },
    allowPositionals: true,
  });

  if (values.help || positionals.length === 0) {
    printUsage();
    process.exit(values.help ? 0 : 1);
  }

  if (!UNSPLASH_ACCESS_KEY) {
    console.error("Error: UNSPLASH_ACCESS_KEY environment variable is not set");
    console.error("Get your API key at: https://unsplash.com/developers");
    process.exit(1);
  }

  const query = positionals.join(" ");
  const count = Math.min(parseInt(values.count || "1"), 10);
  const outputDir = values.output || ".";
  const orientation = values.orientation;
  const size = values.size || "regular";

  console.log(`Searching for "${query}"...`);

  try {
    // Ensure output directory exists
    await mkdir(outputDir, { recursive: true });

    // Search for photos
    const photos = await searchPhotos(query, { count, orientation });

    if (photos.length === 0) {
      console.log("No photos found for this query.");
      process.exit(0);
    }

    console.log(`Found ${photos.length} photo(s). Downloading...\n`);

    const downloaded: string[] = [];

    for (const photo of photos.slice(0, count)) {
      try {
        const filepath = await downloadImage(photo, outputDir, size);
        downloaded.push(filepath);
        console.log(`Downloaded: ${filepath}`);
        printAttribution(photo);
        console.log();
      } catch (err) {
        console.error(`Failed to download ${photo.id}: ${err}`);
      }
    }

    console.log(`\nSuccessfully downloaded ${downloaded.length} image(s).`);

    // Print attribution reminder
    console.log("\n--- Attribution Reminder ---");
    console.log("When using Unsplash images, include attribution:");
    console.log('  "Photo by [Photographer] on Unsplash"');
    console.log("  with links to both the photographer and Unsplash.");
  } catch (err) {
    console.error(`Error: ${err}`);
    process.exit(1);
  }
}

main();
