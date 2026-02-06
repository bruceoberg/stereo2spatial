// Pair2Spatial.swift
//
// Combines a left-eye and right-eye image into a stereo HEIC spatial photo
// compatible with Apple Vision Pro.
//
// Usage: pair2spatial <left-image> <right-image> <output.heic> [--fov <degrees>] [--baseline <mm>]

import Foundation
import ImageIO
import UniformTypeIdentifiers

// MARK: - Argument parsing

struct Args {
    let pathLeft: String
    let pathRight: String
    let pathOutput: String
    let degFovHorizontal: Double
    let mmBaseline: Double
}

func parseArgs() -> Args {
    let lArg = Array(CommandLine.arguments.dropFirst())

    guard lArg.count >= 3 else {
        fputs("""
            Usage: pair2spatial <left-image> <right-image> <output.heic> [--fov <degrees>] [--baseline <mm>]

            Options:
              --fov <degrees>      Horizontal field of view (default: 55.0)
              --baseline <mm>      Stereo baseline in millimeters (default: 65.0)

            """, stderr)
        exit(1)
    }

    let pathLeft = lArg[0]
    let pathRight = lArg[1]
    let pathOutput = lArg[2]

    var degFov = 55.0
    var mmBaseline = 65.0

    var iArg = 3
    while iArg < lArg.count {
        switch lArg[iArg] {
        case "--fov":
            guard iArg + 1 < lArg.count, let val = Double(lArg[iArg + 1]) else {
                fputs("Error: --fov requires a numeric value\n", stderr)
                exit(1)
            }
            degFov = val
            iArg += 2

        case "--baseline":
            guard iArg + 1 < lArg.count, let val = Double(lArg[iArg + 1]) else {
                fputs("Error: --baseline requires a numeric value\n", stderr)
                exit(1)
            }
            mmBaseline = val
            iArg += 2

        default:
            fputs("Error: unknown argument '\(lArg[iArg])'\n", stderr)
            exit(1)
        }
    }

    return Args(
        pathLeft: pathLeft,
        pathRight: pathRight,
        pathOutput: pathOutput,
        degFovHorizontal: degFov,
        mmBaseline: mmBaseline
    )
}

// MARK: - Image loading

func loadCGImage(path: String) -> CGImage {
    let url = URL(fileURLWithPath: path)

    guard let source = CGImageSourceCreateWithURL(url as CFURL, nil) else {
        fputs("Error: could not create image source from '\(path)'\n", stderr)
        exit(1)
    }

    guard let image = CGImageSourceCreateImageAtIndex(source, 0, nil) else {
        fputs("Error: could not decode image from '\(path)'\n", stderr)
        exit(1)
    }

    return image
}

// MARK: - Spatial HEIC creation

func createSpatialPhoto(
    imgLeft: CGImage,
    imgRight: CGImage,
    pathOutput: String,
    degFovHorizontal: Double,
    mmBaseline: Double
) {
    let url = URL(fileURLWithPath: pathOutput)

    guard let destination = CGImageDestinationCreateWithURL(
        url as CFURL,
        UTType.heic.identifier as CFString,
        2,
        nil
    ) else {
        fputs("Error: could not create HEIC image destination\n", stderr)
        exit(1)
    }

    // Compute camera intrinsics from horizontal FOV.
    //
    // The intrinsics matrix is:
    //   [ fx  0  cx ]
    //   [  0  fy cy ]
    //   [  0   0  1 ]
    //
    // where fx = fy = focalLengthPixels, cx = width/2, cy = height/2.

    let gWidth = Double(imgLeft.width)
    let gHeight = Double(imgLeft.height)
    let radFovHorizontal = degFovHorizontal * (.pi / 180.0)
    let gFocalLengthPixels = 0.5 * gWidth / tan(0.5 * radFovHorizontal)

    let lGIntrinsics: [CGFloat] = [
        CGFloat(gFocalLengthPixels), 0, CGFloat(gWidth / 2.0),
        0, CGFloat(gFocalLengthPixels), CGFloat(gHeight / 2.0),
        0, 0, 1,
    ]

    let properties: [CFString: Any] = [
        kCGImagePropertyGroups: [
            kCGImagePropertyGroupIndex: 0,
            kCGImagePropertyGroupType: kCGImagePropertyGroupTypeStereoPair,
            kCGImagePropertyGroupImageIndexLeft: 0,
            kCGImagePropertyGroupImageIndexRight: 1,
        ] as [CFString: Any],
        kCGImagePropertyHEIFDictionary: [
            kIIOMetadata_CameraModelKey: [
                kIIOCameraModel_Intrinsics: lGIntrinsics as CFArray,
            ] as [CFString: Any],
        ] as [CFString: Any],
    ]

    CGImageDestinationAddImage(destination, imgLeft, properties as CFDictionary)
    CGImageDestinationAddImage(destination, imgRight, properties as CFDictionary)

    guard CGImageDestinationFinalize(destination) else {
        fputs("Error: failed to finalize HEIC output\n", stderr)
        exit(1)
    }
}

// MARK: - Main

let args = parseArgs()

let imgLeft = loadCGImage(path: args.pathLeft)
let imgRight = loadCGImage(path: args.pathRight)

// Sanity check: both images should be the same size.

if imgLeft.width != imgRight.width || imgLeft.height != imgRight.height {
    fputs(
        "Warning: left (\(imgLeft.width)x\(imgLeft.height)) and right "
        + "(\(imgRight.width)x\(imgRight.height)) images differ in size\n",
        stderr
    )
}

createSpatialPhoto(
    imgLeft: imgLeft,
    imgRight: imgRight,
    pathOutput: args.pathOutput,
    degFovHorizontal: args.degFovHorizontal,
    mmBaseline: args.mmBaseline
)

let cBytesOutput = try FileManager.default
    .attributesOfItem(atPath: args.pathOutput)[.size] as? Int ?? 0

fputs("Created \(args.pathOutput) (\(cBytesOutput) bytes)\n", stderr)
