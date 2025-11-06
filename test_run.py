import asyncio
import traceback
from FoldingAtHomeControl import FoldingAtHomeController


EMAIL = "..."

PASSPHRASE = "..."


def callback(message_type, data):
    print(f"callback for: {message_type}: ", data)


async def cancel_task(task_to_cancel: asyncio.Task):
    task_to_cancel.cancel()
    await task_to_cancel


async def run_cmds(ctrller: FoldingAtHomeController):
    while True:
        while not ctrller.is_connected:
            print("connected ", ctrller.is_connected)
            await asyncio.sleep(1)

        await ctrller.pause_all_slots_async()
        await asyncio.sleep(5)
        await ctrller.unpause_all_slots_async()
        await asyncio.sleep(5)


if __name__ == "__main__":
    Controller = FoldingAtHomeController(EMAIL, PASSPHRASE)
    Controller.register_callback(callback)
    loop = asyncio.get_event_loop()
    task = loop.create_task(Controller.start())
    try:
        loop.run_until_complete(
            asyncio.gather(task, loop.create_task(run_cmds(Controller)))
        )

    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(e)
        traceback.print_exception(e)
    finally:
        print("Cancelling task")
        try:
            loop.run_until_complete(cancel_task(task))
        except asyncio.CancelledError:
            print("Closing Loop")
            loop.close()
