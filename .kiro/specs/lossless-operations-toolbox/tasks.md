# Implementation Plan: Lossless Operations Toolbox

## Overview

This implementation plan creates a specialized script based on the Universal Toolbox approach, focused exclusively on lossless video operations. The script will leverage FFmpeg's stream copy capabilities to provide fast, quality-preserving video operations through a simplified, curated interface.

## Tasks

- [x] 1. Set up project structure and core FFmpeg integration
  - Create script directory structure following Universal Toolbox patterns
  - Set up FFmpeg wrapper with stream copy validation
  - Implement basic codec analysis using FFprobe
  - Create core data models for file processing state
  - _Requirements: 7.1, 7.4_

- [ ] 2. Implement codec compatibility validation system
  - [x] 2.1 Create codec analyzer with FFprobe integration
    - Build comprehensive codec information extraction
    - Implement container-codec compatibility matrix
    - Add support for H.264, H.265, VP8, VP9, AV1 video codecs
    - Add support for AAC, MP3, Opus, FLAC audio codecs
    - _Requirements: 7.1, 7.4_

  - [x] 2.2 Write property test for codec analysis accuracy
    - **Property 11: Codec Analysis Accuracy**
    - **Validates: Requirements 7.1, 7.2, 7.4**

  - [x] 2.3 Implement compatibility validation for operations
    - Create validation logic for trimming, remuxing, merging operations
    - Build compatibility checker for multi-file operations
    - Implement transcoding prevention with clear error messages
    - _Requirements: 5.1, 5.2, 5.4_

  - [x] 2.4 Write property test for lossless operation validation
    - **Property 2: Lossless Operation Validation**
    - **Validates: Requirements 2.4, 3.3, 5.1, 5.2, 5.4, 5.5**

- [ ] 3. Build core lossless operation engines
  - [x] 3.1 Implement trimming engine with stream copy
    - Create trimming operation with start/end timestamp support
    - Implement keyframe-accurate cutting within codec constraints
    - Add validation for time range and file duration
    - Generate FFmpeg commands using `-c copy` for stream preservation
    - _Requirements: 1.1, 1.5_

  - [x] 3.2 Write property test for trimming accuracy
    - **Property 3: Trimming Accuracy**
    - **Validates: Requirements 1.1, 1.5**

  - [x] 3.3 Implement container remuxing engine
    - Create format conversion between MP4, MKV, MOV, WebM
    - Implement codec-container compatibility validation
    - Add stream copy verification for remuxing operations
    - Generate appropriate FFmpeg remuxing commands
    - _Requirements: 2.1, 2.2, 2.3_

  - [x] 3.4 Write property test for container format remuxing
    - **Property 4: Container Format Remuxing**
    - **Validates: Requirements 2.2, 2.3**

- [x] 4. Checkpoint - Core operations functional
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Implement file merging and stream management
  - [x] 5.1 Create file concatenation engine
    - Implement multi-file codec compatibility validation
    - Build concatenation using FFmpeg concat demuxer with stream copy
    - Add metadata preservation during merging operations
    - Create error handling for incompatible file combinations
    - _Requirements: 3.1, 3.2, 3.5_

  - [x] 5.2 Write property test for codec compatibility validation
    - **Property 5: Codec Compatibility Validation**
    - **Validates: Requirements 3.1, 3.3**

  - [x] 5.3 Implement stream selection and metadata editing
    - Create audio/video/subtitle track selection functionality
    - Implement metadata editing without stream modification
    - Add rotation metadata changes (without actual video rotation)
    - Build stream copy preservation for retained tracks
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [x] 5.4 Write property test for stream selection accuracy
    - **Property 7: Stream Selection Accuracy**
    - **Validates: Requirements 4.2**

  - [x] 5.5 Write property test for metadata-only rotation
    - **Property 8: Metadata-Only Rotation**
    - **Validates: Requirements 4.4**

- [ ] 6. Build batch processing system
  - [x] 6.1 Implement batch operation controller
    - Create multi-file processing with individual validation
    - Build progress tracking for each file in batch
    - Implement selective processing (skip incompatible files)
    - Add detailed error reporting and summary generation
    - _Requirements: 6.1, 6.2, 6.3, 6.5_

  - [x] 6.2 Write property test for batch processing integrity
    - **Property 10: Batch Processing Integrity**
    - **Validates: Requirements 6.1, 6.2, 6.3, 6.5**

- [ ] 7. Create user interface following Universal Toolbox patterns
  - [x] 7.1 Build simplified script interface
    - Create main interface focused on lossless operations only
    - Implement file selection and operation choice UI
    - Add clear indicators for lossless vs transcoding operations
    - Build progress display consistent with Universal Toolbox style
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

  - [x] 7.2 Write property test for UI lossless operation indication
    - **Property 14: UI Lossless Operation Indication**
    - **Validates: Requirements 8.2, 8.5**

  - [x] 7.3 Implement error handling and user feedback
    - Create comprehensive error message system
    - Add alternative operation suggestions for incompatible requests
    - Implement graceful handling of processing interruptions
    - Build user guidance for resolving common issues
    - _Requirements: 5.3, 7.5_

  - [x] 7.4 Write property test for alternative suggestions
    - **Property 9: Alternative Suggestions**
    - **Validates: Requirements 5.3**

- [ ] 8. Add comprehensive property-based testing
  - [x] 8.1 Write property test for stream copy preservation
    - **Property 1: Stream Copy Preservation**
    - **Validates: Requirements 1.2, 1.3, 2.1, 2.5, 3.2, 4.1, 4.3, 4.5**

  - [x] 8.2 Write property test for metadata preservation
    - **Property 6: Metadata Preservation**
    - **Validates: Requirements 3.5**

  - [x] 8.3 Write property test for multi-file compatibility analysis
    - **Property 12: Multi-File Compatibility Analysis**
    - **Validates: Requirements 7.3**

  - [x] 8.4 Write property test for unsupported codec handling
    - **Property 13: Unsupported Codec Handling**
    - **Validates: Requirements 7.5**

  - [x] 8.5 Write property test for stream copy command generation
    - **Property 15: Stream Copy Command Generation**
    - **Validates: Requirements 9.2**

  - [x] 8.6 Write property test for processing time estimation
    - **Property 16: Processing Time Estimation**
    - **Validates: Requirements 9.5**

- [ ] 9. Integration and final testing
  - [x] 9.1 Wire all components together
    - Integrate all engines into main script interface
    - Connect validation system with operation engines
    - Link batch processing with individual operation handlers
    - Ensure consistent error handling across all components
    - _Requirements: All requirements integration_

  - [x] 9.2 Write integration tests for end-to-end workflows
    - Test complete workflows from file selection to output
    - Verify error handling across component boundaries
    - Test batch processing with mixed file types
    - _Requirements: All requirements integration_

- [x] 10. Final checkpoint - Complete system validation
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Each task references specific requirements for traceability
- Property tests validate universal correctness properties from the design document
- The script follows Universal Toolbox patterns but simplified for lossless operations only
- All operations must use FFmpeg stream copy to ensure zero quality loss
- Checkpoints ensure incremental validation and user feedback opportunities
- Comprehensive testing approach ensures reliability from the start