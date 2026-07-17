# POSSIBLE-ENHANCEMENT-010 — Possible enhancement — include frontend source and reproducible build metadata

[← Audit index](../README.md)

| Field | Value |
|---|---|
| Classification | **Possible enhancement** |
| Severity | **Enhancement** |
| Confidence | **High** |
| Area | Build and reviewability |
| Components | OpenHop Repeater Web UI |
| Audit date | 2026-07-17 |
| Status | Open in supplied snapshot |

## TL;DR

The supplied repository contains compiled/minified JavaScript assets but no corresponding Vue/TypeScript source or source maps.

## What happens now

Logical UI defects can be located by byte offset, but safe changes require editing generated one-line bundles or finding an external source snapshot.

## Expected behaviour / proposed direction

Include the frontend source tree, lockfile, build command and source maps (or documented separate source repository/revision) with releases.

## What needs to change

Enables code review, targeted patches, static typing and deterministic bundle regeneration.

## Suggested code change

> **Review warning:** the linked patch is an LLM-generated implementation sketch. It is intended to show the approximate change surface, not to be applied blindly. Rebase it onto the real frontend source where compiled assets are involved, add regression tests, and review hardware/runtime implications.

[Open the suggested patch](../patches/POSSIBLE-ENHANCEMENT-010.patch)

## Source references and excerpts

_No single source excerpt; this is a repository/build-layout observation._
