// Metadata-only CoreBluetooth probe. Never connects, pairs, reads or writes EEG.
import Foundation
import CoreBluetooth

let service = CBUUID(string: "0000FE8D-0000-1000-8000-00805F9B34FB")
let requestPermission = CommandLine.arguments.contains("--request-permission")
let shouldScan = !CommandLine.arguments.contains("--no-scan")

func authorizationName() -> String {
    switch CBManager.authorization {
    case .allowedAlways: return "allowed"
    case .denied: return "denied"
    case .restricted: return "restricted"
    case .notDetermined: return "not_requested"
    @unknown default: return "unknown"
    }
}

final class Probe: NSObject, CBCentralManagerDelegate {
    var central: CBCentralManager!
    var done = false
    var devices: [String: [String: Any]] = [:]
    var power = "unknown"
    var scanning = false
    func finish() {
        guard !done else { return }
        done = true
        central?.stopScan()
        let result: [String: Any] = ["authorization": authorizationName(), "power": power,
            "devices": Array(devices.values), "scan_performed": scanning,
            "scope": "Muse FE8D service only; system connection or advertising metadata; no pairing or EEG"]
        if let bytes = try? JSONSerialization.data(withJSONObject: result, options: [.sortedKeys]),
           let output = String(data: bytes, encoding: .utf8) { print(output) }
    }
    func centralManagerDidUpdateState(_ manager: CBCentralManager) {
        switch manager.state {
        case .poweredOn:
            power = "on"
            for device in manager.retrieveConnectedPeripherals(withServices: [service]).prefix(8) {
                devices[device.identifier.uuidString] = ["id": device.identifier.uuidString,
                    "name": String((device.name ?? "Muse service device").prefix(80)),
                    "system_connected": true, "advertising": false]
            }
            if shouldScan {
                scanning = true
                manager.scanForPeripherals(withServices: [service], options: [CBCentralManagerScanOptionAllowDuplicatesKey: false])
                DispatchQueue.main.asyncAfter(deadline: .now() + 2) { self.finish() }
            } else { finish() }
        case .poweredOff: power = "off"; finish()
        case .unauthorized: power = "unknown"; finish()
        case .unsupported: power = "unsupported"; finish()
        case .resetting: power = "resetting"
        case .unknown: power = "unknown"
        @unknown default: power = "unknown"; finish()
        }
    }
    func centralManager(_ manager: CBCentralManager, didDiscover device: CBPeripheral,
                        advertisementData: [String: Any], rssi RSSI: NSNumber) {
        guard devices.count < 8 || devices[device.identifier.uuidString] != nil else { return }
        let wasConnected = devices[device.identifier.uuidString]?["system_connected"] as? Bool ?? false
        devices[device.identifier.uuidString] = ["id": device.identifier.uuidString,
            "name": String((device.name ?? advertisementData[CBAdvertisementDataLocalNameKey] as? String ?? "Muse service device").prefix(80)),
            "system_connected": wasConnected, "advertising": true, "rssi_dbm": RSSI]
    }
}

let probe = Probe()
if authorizationName() != "not_requested" || requestPermission {
    probe.central = CBCentralManager(delegate: probe, queue: .main,
        options: [CBCentralManagerOptionShowPowerAlertKey: false])
    DispatchQueue.main.asyncAfter(deadline: .now() + 5) { probe.finish() }
    while !probe.done { RunLoop.main.run(until: Date(timeIntervalSinceNow: 0.05)) }
} else { probe.finish() }
