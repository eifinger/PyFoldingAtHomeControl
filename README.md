# PyFoldingAtHomeControl - BETA
Python library to get stats from your Folding@Home Clients

[![GitHub Actions](https://github.com/eifinger/PyFoldingAtHomeControl/workflows/Python%20package/badge.svg)](https://github.com/eifinger/PyFoldingAtHomeControl/actions?workflow=Python+package)
[![PyPi](https://img.shields.io/pypi/v/PyFoldingAtHomeControl.svg)](https://pypi.python.org/pypi/PyFoldingAtHomeControl)
[![PyPi](https://img.shields.io/pypi/l/PyFoldingAtHomeControl.svg)](https://github.com/eifinger/PyFoldingAtHomeControl/blob/master/LICENSE)
[![codecov](https://codecov.io/gh/eifinger/PyFoldingAtHomeControl/branch/master/graph/badge.svg)](https://codecov.io/gh/eifinger/PyFoldingAtHomeControl)
[![Downloads](https://pepy.tech/badge/pyfoldingathomecontrol)](https://pepy.tech/project/pyfoldingathomecontrol)

## Installation

```bash
$ pip install PyFoldingAtHomeControl
```

## Usage

```python
import asyncio
from FoldingAtHomeControl import FoldingAtHomeController
from FoldingAtHomeControl import PyOnMessageTypes


def callback(message_type, data):
    print(f"callback for: {message_type}: ", data)


async def cancel_task(task_to_cancel):
    task_to_cancel.cancel()
    await task_to_cancel


if __name__ == '__main__':
    Controller = FoldingAtHomeController("localhost")
    Controller.register_callback(callback)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(Controller.try_connect_async(5))
    loop.run_until_complete(Controller.subscribe_async())
    task = loop.create_task(Controller.start())
    try:
        loop.run_until_complete(task)
    except KeyboardInterrupt:
        pass
    finally:
        print("Cancelling task")
        try:
            loop.run_until_complete(cancel_task(task))
        except asyncio.CancelledError:
            print("Closing Loop")
            loop.close()
```
