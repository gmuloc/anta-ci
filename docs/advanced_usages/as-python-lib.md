# How to use ANTA as a Python Library

ANTA has been built to allow user to embeded its tools in your own application. This section describes how you can leverage ANTA modules to help you create your own NRFU solution.

## Inventory Manager

AntaInventory class is in charge of creating a list of hosts with their information and an eAPI session ready to be consummed. To do that, it connects to all devices to check reachability and ensure eAPI is running.

```python
from anta.inventory import AntaInventory

inventory = AntaInventory.parse(
    inventory_file="inventory.yml",
    username="username",
    password="password",
    enable_password="enable",
    timeout=1,
)
```

Then it is easy to get all devices or only active devices with the following method:

```python
# print the non reachable devices
for device in inventory.get_inventory(established_only=False):
    if device.established is False:
        print(f"Could not connect to device {device.host}")

# run an EOS commands list on the reachable devices from the inventory
for device in inventory.get_inventory(established_only=True):
    device.session.runCmds(
        1, ["show version", "show ip bgp summary"]
    )
```

You can find the ANTA Inventory module [here](../api/inventory.md).

??? note "How to create your inventory file"
    Please visit this [dedicated section](../usage-inventory-catalog.md) for how to use inventory and catalog files.


## Use tests from ANTA

All the test functions are based on the exact same input and returns a generic structure with different information.

### Test input

Any test input is based on an `InventoryDevice` object and a list of options. Here is an example to check uptime and check it is higher than `minimum` option.

```python
def verify_uptime(device: InventoryDevice, minimum: int = None) -> TestResult:
```

In general, [`InventoryDevice`](../api/inventory.models.md) is an object created by `AntaInventory`. But it can be manually generated by following required data model.

Here is an example of a list of `InventoryDevice`

```python
[
    {
        "InventoryDevice(host=IPv4Address('192.168.0.17')",
        "username='ansible'",
        "password='ansible'",
        "session=<ServerProxy for ansible:ansible@192.168.0.17/command-api>",
        "url='https://ansible:ansible@192.168.0.17/command-api'",
        "established=True",
        "is_online=True",
        "hw_model=cEOS-LAB",
    },

    {
        "InventoryDevice(host=IPv4Address('192.168.0.2')",
        "username='ansible'",
        "password='ansible'",
        "session=None",
        "url='https://ansible:ansible@192.168.0.2/command-api'",
        "established=False"
        "is_online=False",
        "tags": ['dc1', 'spine', 'pod01'],
        "hw_model=unset",
    }
]
```

### Test output

All tests return a TestResult structure with the following elements:

- `result`: Can be `success`, `skipped`, `failure`, `error` and report result of the test
- `host`: IP address of the tested device
- `test`: Test name runs on `host`
- `message`: Optional message returned by the test.

### Test structure

All tests are built on a class named `AntaTest` which provides a complete toolset for a test:

- Object creation
- Test definition
- TestResult definition
- Abstracted method to collect data

This approach means each time you create a test it will be based on this `AntaTest` class. Besides that, you will have to provide some elements:

- `name`: Name of the test
- `description`: A human readable description of your test
- `categories`: a list of categories to sort test.
- `commands`: a list of command to run. This list _must_ be a list of `AntaCommand` which is described in the next part of this document.

Here is an example of a hardware test related to device temperature:

```python
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, cast

from anta.models import AntaTest, AntaCommand


class VerifyTemperature(AntaTest):
    """
    Verifies device temparture is currently OK.
    """

    name = "VerifyTemperature"
    description = "Verifies device temparture is currently OK"
    categories = ["hardware"]
    commands = [AntaCommand(command="show system environment temperature", ofmt="json")]

    @AntaTest.anta_test
    def test(self) -> None:
        """Run VerifyTemperature validation"""
        command_output = cast(Dict[str, Dict[Any, Any]], self.instance_commands[0].output)
        temperature_status = command_output["systemStatus"] if "systemStatus" in command_output.keys() else ""
        if temperature_status == "temperatureOk":
            self.result.is_success()
        else:
            self.result.is_failure(f"Device temperature is not OK, systemStatus: {temperature_status }")
```

When you run the test, object will automatically call its `anta.models.AntaTest.collect()` method to get device output. This method does a loop to call `anta.inventory.models.InventoryDevice.collect()` methods which is in charge of managing device connection and how to get data.

??? info "run test offline"
    You can also pass eos data directly to your test if you want to validate data collected in a different workflow. An example is provided below just for information:

    ```python
    test = VerifyTemperature(mocked_device, eos_data=test_data["eos_data"])
    asyncio.run(test.test())
    ```

test function is always the same and __must__ be defined with the `@AntaTest.anta_test` decorator. This function takes at least one argument which is a `anta.inventory.models.InventoryDevice` object and can have multiple additional parameters depending of your test definition. All parameters __must__ come with a default value and the test function __should__ validate the parameters values.

```python
class VerifyTemperature(AntaTest):
    ...
    @AntaTest.anta_test
    def test(self) -> None:
        pass

class VerifyTransceiversManufacturers(AntaTest):
    ...
    @AntaTest.anta_test
    def test(self, manufacturers: Optional[List[str]] = None) -> None:
        pass
```

The test itself does not return any value, but the result is directly availble from your object and exposes a `anta.result_manager.models.TestResult` object with result, name of the test and optional messages.

```python
from anta.tests.hardware import VerifyTemperature

test = VerifyTemperature(mocked_device, eos_data=test_data["eos_data"])
asyncio.run(test.test())
assert test.result.result == "success"
```

### Commands for test

To make it easier to get data, ANTA defines 2 different classes to manage commands to send to device:

#### `anta.models.AntaCommand`

Abstract a command with following information:

- Command to run,
- Ouput format expected
- eAPI version
- Output of the command

Usage example:

```python
from anta.models import AntaCommand

cmd1 = AntaCommand(command="show zerotouch")
cmd2 = AntaCommand(command="show running-config diffs", ofmt="text")
```

#### `anta.models.AntaTemplate`

Because some command can require more dynamic than just a command with no parameter provided by user, ANTA supports command template: you define a template in your test class and user provide parameters when creating test object.

```python

class RunArbitraryTemplateCommand(AntaTest):
    """
    Run an EOS command and return result
    Based on AntaTest to build relevant output for pytest
    """

    name = "Run aributrary EOS command"
    description = "To be used only with anta debug commands"
    template = AntaTemplate(template="show interfaces {ifd}")
    categories = ["debug"]

    @AntaTest.anta_test
    def test(self) -> None:
        errdisabled_interfaces = [interface for interface, value in response["interfaceStatuses"].items() if value["linkStatus"] == "errdisabled"]
        ...


params = [{"ifd": "Ethernet2"}, {"ifd": "Ethernet49/1"}]
run_command1 = RunArbitraryTemplateCommand(device_anta, params)
```

In this example, test waits for interfaces to check from user setup and will only check for interfaces in `params`
