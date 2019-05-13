#!/usr/bin/env python3

import format
import idl
import strings
import tycheck

import argparse
import io
import json
import os
import random
import subprocess
import sys

def main():
    parser = argparse.ArgumentParser()
    parser.set_defaults(func=lambda args: print('use --help to see commands'))
    parser.add_argument('--dir', help='Directory to sample/encode', nargs='+', required=True)
    parser.add_argument('--seed', help='Seed value', default=0, type=int)
    parser.add_argument('--sampling', help='Sample probability. 0 = no dictionary', default=0.2, type=float)
    parser.add_argument('--binjs_encode', help='Path to binjs_encode', required=True)
    parser.add_argument('--show_errors', help='Show errors', default=False, type=bool)
    parser.add_argument('--apply-brotli', help='Apply brotli after encoding', default=False, type=bool)
    args = parser.parse_args()

    sys.setrecursionlimit(10000)

    # Initialize grammar
    grammar = idl.parse_es6_idl()
    ty_script = grammar.interfaces['Script']
    float_fixer = tycheck.FloatFixer(grammar)

    # Initialize RNG
    rng = random.Random(None)
    rng.seed(args.seed)

    # The files we're going to use to extract a dictionary.
    dictionary_group = []

    # The files we're going to use to test compression level.
    control_group = []

    # Walk subdirectories and sort files to dictionary group / control group.
    for root in args.dir:
        for local, _, paths in os.walk(root):
            if local.find(".git") != -1:
                # Skip .git subdirectory
                continue
            for path in paths:
                print("Let's look at %s" % [path])
                full_path = os.path.join(local, path)
                if rng.random() < args.sampling:
                    dictionary_group.append(full_path)
                else:
                    control_group.append(full_path)

    # Prepare dictionary
    print("Preparing dictionary")
    dictionary_sources = []
    for i, path in enumerate(dictionary_group):
        print("%(index)d/%(len)d Adding %(path)s to dictionary" % {"path": path, "index": i, "len": len(dictionary_group)})
        proc = subprocess.run([args.binjs_encode, "--quiet", "--show-ast", "-i", path, "-o", "/tmp/binjs"], capture_output=True)

        if proc.returncode != 0:
            # Skip if the file somehow can't be processed.
            print("...skipping (cannot parse)")
            if args.show_errors:
                print(proc.stderr)
            continue

        if len(proc.stdout) == 0:
            # We can't handle empty files.
            continue

        try:
            ast = json.loads(proc.stdout)
            float_fixer.rewrite(ty_script, ast)
            dictionary_sources.append((ty_script, ast))
        except Exception as e:
            print("... skipping (cannot process)")
            if args.show_errors:
                print(e)
            continue

    strings_dictionary = strings.prepare_dict(grammar, dictionary_sources)


    # Compress with dictionary
    print("Compressing with dictionary")
    total_encoded_size = 0
    total_unencoded_brotli_size = 0
    for i, path in enumerate(control_group):
        print("%(index)d/%(len)d Compressing %(path)s with dictionary" % {"path": path, "index": i, "len": len(control_group)})
        TMP_DEST_PATH = "/tmp/encoded.binjs"

        # Execute external binjs_encode to parse JavaScript
        proc = subprocess.run([args.binjs_encode, "--quiet", "--show-ast", "-i", path, "-o", "/tmp/binjs"], capture_output=True)
        if proc.returncode != 0:
            # Skip if the file somehow can't be processed.
            print("...skipping (cannot parse)")
            if args.show_errors:
                print(proc.stderr)
            continue

        if len(proc.stdout) == 0:
            # We can't handle empty files.
            continue

        ast = None
        try:
            # Rewrite integer literals which should be floating point numbers
            ast = json.loads(proc.stdout)
            float_fixer.rewrite(ty_script, ast)
        except Exception as e:
            print("... skipping (cannot process)")
            if args.show_errors:
                print(e)
            continue

        # Encode file
        dest = open(TMP_DEST_PATH, 'wb')
        format.write(grammar, strings_dictionary, ty_script, ast, dest)
        dest.close()

        len_encoded = 0
        if args.apply_brotli:
            # Compress encoded version
            proc = subprocess.run(["brotli", "--stdout", TMP_DEST_PATH, "--best"], capture_output=True)
            proc.check_returncode()
            encoded_brotli = proc.stdout
            len_encoded = len(encoded_brotli)
        else:
            len_encoded = os.stat(TMP_DEST_PATH).st_size

        total_encoded_size += len_encoded

        # Compress unencoded version, for comparison
        proc = subprocess.run(["brotli", "--stdout", path, "--best"], capture_output=True)
        proc.check_returncode()
        raw_brotli = proc.stdout
        total_unencoded_brotli_size += len(raw_brotli)

        print("... ratio: %f" % (len_encoded / len(raw_brotli)))
        print("... global ratio so far: %f" % (total_encoded_size / total_unencoded_brotli_size))

    print("Run complete")
    print("Global ratio: %f" % (total_encoded_size / total_unencoded_brotli_size))

if __name__ == '__main__':
  main()
