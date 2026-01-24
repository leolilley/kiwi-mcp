# Dependency Warnings Analysis

**Date:** 2026-01-24  
**Status:** Reviewed and Documented

## Summary

After running all tests with deprecation warnings enabled, we identified several dependency warnings. Most are from third-party libraries and cannot be fixed directly in our codebase.

## Warnings Identified

### 1. ✅ Fixed: pytest.mark.version Custom Mark

**Status:** ✅ **FIXED**

**Issue:** Custom pytest marker `@pytest.mark.version` was not registered, causing warnings during test collection.

**Resolution:** Added the marker to `pytest.ini`:
```ini
version: Tests related to version checking and warnings
```

**Impact:** No functional impact, just cleaner test output.

---

### 2. ⚠️ Third-Party: pyiceberg Deprecation Warnings

**Status:** ⚠️ **CANNOT FIX** (Third-party library)

**Warnings:**
```
DeprecationWarning: 'enablePackrat' deprecated - use 'enable_packrat'
DeprecationWarning: 'escChar' argument is deprecated, use 'esc_char'
DeprecationWarning: 'unquoteResults' argument is deprecated, use 'unquote_results'
```

**Source:** `pyiceberg/expressions/parser.py` (lines 72, 85)

**Dependency Chain:**
- `pyiceberg` (v0.10.0) is a **transitive dependency**
- Required by: `storage3`
- `storage3` is required by: `supabase`

**Action Required:** None - This is an issue in the `pyiceberg` library that will be fixed when they update their code. We cannot fix this directly.

**Tracking:** Monitor `pyiceberg` releases for fixes. Consider pinning `storage3` version if needed.

---

### 3. ⚠️ Third-Party: supabase Deprecation Warnings

**Status:** ⚠️ **CANNOT FIX** (Third-party library)

**Warnings:**
```
DeprecationWarning: The 'timeout' parameter is deprecated. Please configure it in the http client instead.
DeprecationWarning: The 'verify' parameter is deprecated. Please configure it in the http client instead.
```

**Source:** `supabase/_sync/client.py` (line 309)

**Our Usage:** We use `create_client(url, key)` without passing deprecated parameters:
- `kiwi_mcp/api/base.py:23`
- `kiwi_mcp/storage/vector/registry.py:28`

**Action Required:** None - The warnings are coming from inside the `supabase` library itself, not from our code. We are not using the deprecated parameters.

**Tracking:** Monitor `supabase` releases (currently v2.27.2). The library maintainers will need to update their internal code.

---

## Test Results Summary

- **Total Tests:** 563
- **Passing:** ~500+ (exact count varies)
- **Failing:** ~60 (unrelated to dependency warnings)
- **Errors:** ~10 (unrelated to dependency warnings)

The failing tests are due to:
- Missing script handler (migrated to tool handler)
- Test setup issues
- Vector storage dependency issues (chromadb, sentence-transformers)

These are separate issues from dependency warnings.

---

## Recommendations

### Immediate Actions
1. ✅ **DONE:** Register `pytest.mark.version` custom marker
2. ✅ **DONE:** Document all dependency warnings

### Future Monitoring
1. **Watch pyiceberg releases:** Check for updates that fix deprecation warnings
2. **Watch supabase releases:** Monitor for internal fixes to deprecated parameter usage
3. **Consider dependency pinning:** If warnings become errors in future Python versions, consider pinning transitive dependencies

### Suppression (If Needed)
If warnings become too noisy, we can suppress them in `pytest.ini`:
```ini
filterwarnings =
    ignore::DeprecationWarning:pyiceberg.*
    ignore::DeprecationWarning:supabase.*
```

**Note:** Currently warnings are already being ignored in `pytest.ini` (line 57-58), but they still show up when explicitly enabled with `-W default::DeprecationWarning`.

---

## Conclusion

**All actionable warnings have been addressed.** The remaining warnings are from third-party libraries and will be resolved when those libraries update their code. No changes are needed in our codebase.
