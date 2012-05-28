in development:

- Avoid busy-looping (add time.sleep) when waiting for responses.
- Allow user to pass in value `0` for `sl` argument in `verify` and `verify_multi` method
- Throw an exception inside `verify` and `verify_multi` method if timeout has
  occurred or invalid status code is returned
- Add logging
