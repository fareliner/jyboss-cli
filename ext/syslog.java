/**
 * Copyright (C) 2007 Matt Shelton.
 *
 * @author Matt Shelton <matt@mattshelton.com>
 * @version $Id$
 */

import java.io.IOException;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;
import java.net.SocketException;
import java.net.UnknownHostException;

/**
 * This module provides an interface to the UNIX syslog daemon on the
 * local host.
 *
 * The CPython syslog module uses UNIX domain sockets
 * (http://en.wikipedia.org/wiki/Unix_domain_socket) to communicate with
 * the syslog daemon.  Since domain sockets are not implemented on
 * systems other than UNIX, Java does not support them.  Therefore, this
 * module communicates with the syslog daemon via UDP.
 *
 * In order to use this module, the local syslog daemon must be
 * listening to UDP port 514.  This can be done by starting syslogd with
 * the '-r' switch.
 */
public class syslog {
    // Priority Levels (high to low)
    public static int LOG_EMERG = 0;
    public static int LOG_ALERT = 1;
    public static int LOG_CRIT = 2;
    public static int LOG_ERR = 3;
    public static int LOG_WARNING = 4;
    public static int LOG_NOTICE = 5;
    public static int LOG_INFO = 6;
    public static int LOG_DEBUG = 7;

    // Facilities
    public static int LOG_KERN = 0;
    public static int LOG_USER = 8;
    public static int LOG_MAIL = 16;
    public static int LOG_DAEMON = 24;
    public static int LOG_AUTH = 32;
    public static int LOG_LRP = 48;
    public static int LOG_NEWS = 56;
    public static int LOG_UUCP = 64;
    public static int LOG_CRON = 72;
    public static int LOG_LOCAL0 = 128;
    public static int LOG_LOCAL1 = 136;
    public static int LOG_LOCAL2 = 144;
    public static int LOG_LOCAL3 = 152;
    public static int LOG_LOCAL4 = 160;
    public static int LOG_LOCAL5 = 168;
    public static int LOG_LOCAL6 = 176;
    public static int LOG_LOCAL7 = 184;

    // Log Options
    public static int LOG_PID = 1;
    public static int LOG_CONS = 2;
    public static int LOG_NDELAY = 8;
    public static int LOG_NOWAIT = 16;
    public static int LOG_PERROR = 32;

    // Data used by the module operations.
    private static syslog logger = null;
    private DatagramSocket socket = null;
    private InetAddress daemon = null;
    private String ident = "syslog";
    private int facility = LOG_USER;
    private int logopt = 0;
    private int logmask = 255;

    /**
     * Send a message to the system logger.  Each message is tagged with
     * a priority composed of a <i>facility</i> and a <i>level</i>.
     *
     * @param priority Priority in numeric format.
     * @param message Message to send to the system logger.
     */
    public static void syslog(int priority, String message) {
        // Ensure that there is a syslog instance created.
        if (logger == null)
            openlog();

        // Log the message.
        logger.log(priority, message);
    }

    /**
     * Send a message to the system logger.  The priority defaults at
     * LOG_INFO.
     *
     * @param message Message to send to the system logger.
     */
    public static void syslog(String message) {
        syslog(LOG_INFO, message);
    }

    /**
     * Logging options other than the defaults can be set explicitly
     * opening the log file with <i>openlog()</i> prior to calling
     * <i>syslog()</i>.
     *
     * @param ident A name uniquely identifying the application.
     * @param logopt Syslog Options
     * @param facility Syslog Facility
     */
    public static void openlog(String ident, int logopt, int facility) {
        // Create a new instance of the logger.
        logger = new syslog(ident, logopt, facility);
    }

    /**
     * Logging options other than the defaults can be set explicitly
     * opening the log file with <i>openlog()</i> prior to calling
     * <i>syslog()</i>.  Facility defaults to <b>LOG_USER</b>.
     *
     * @param ident A name uniquely identifying the application.
     * @param logopt Syslog Options
     */
    public static void openlog(String ident, int logopt) {
        openlog(ident, logopt, LOG_USER);
    }

    /**
     * Logging options other than the defaults can be set explicitly
     * opening the log file with <i>openlog()</i> prior to calling
     * <i>syslog()</i>.  Options default to 0 and facility defaults to
     * <b>LOG_USER</b>.
     *
     * @param ident A name uniquely identifying the application.
     */
    public static void openlog(String ident) {
        openlog(ident, 0, LOG_USER);
    }

    /**
     * Default logging options.
     */
    public static void openlog() {
        openlog("syslog", 0, LOG_USER);
    }

    /**
     * Close the log file.
     */
    public static void closelog() {
        logger.close();
        logger = null;
    }

    /**
     * Set the priority mask to <i>maskpri</i> and return the previous
     * mask value.
     *
     * @param maskpri Priority in numeric format.
     * @return Previous mask value.
     */
    public static int setlogmask(int maskpri) {
        // Ensure that there is a syslog instance created.
        if (logger == null)
            openlog();

        // Log the message.
        return logger.setLogmask(maskpri);
    }

    /**
     * For use with <i>setlogmask</i>.  This will mask a single
     * priority.
     *
     * @param pri Priority in numeric format.
     * @return Input suitable for <i>setlogmask</i>.
     */
    public static int LOG_MASK(int pri) {
        return (1 << (pri));
    }

    /**
     * For use with <i>setlogmask</i>.  All priorities through the
     * given priority.
     *
     * @param pri Priority in numeric format.
     * @return Input suitable for <i>setlogmask</i>.
     */
    public static int LOG_UPTO(int pri) {
        return ((1 << ((pri)+1)) - 1);
    }

    /**
     * Create a new instance of the syslog module.
     *
     * @param ident A name uniquely identifying the application.
     * @param logopt Syslog Options
     * @param facility Syslog Facility
     */
    public syslog(String ident, int logopt, int facility) {
        // Open a socket to the localhost.
        try {
            socket = new DatagramSocket();
            daemon = InetAddress.getLocalHost();

        } catch (SocketException ex) {
            // Do nothing, right now.
        } catch (UnknownHostException ex) {
            // Do nothing, right now.
        }

        // Assign logger configuration variables.
        this.ident = ident;
        this.logopt = logopt;
        this.facility = facility;
    }

    /**
     * Send a message to this instance's logger.
     *
     * @param priority The syslog priority of the message.
     * @param message The message to be logged.
     */
    public void log(int priority, String message) {
        // Check the priority against the setlogmask values.
        if ((syslog.LOG_MASK(priority & 0x07) & logmask) == 0)
            return;

        // Construct the message.
        int syslogCode = ((facility << 3) | priority );
        String buffer = "<" + syslogCode + ">" + ident + ": " + message;
        byte[] payload = buffer.getBytes();

        // Construct the UDP packet.
        DatagramPacket packet = new DatagramPacket(
                payload, payload.length, daemon, 514);

        // Send the UDP packet off.
        try {
            socket.send(packet);
        } catch (IOException ex) {
            // Do nothing, yet.
        }
    }

    /**
     * Set the priority mask to <i>maskpri</i> and return the previous
     * mask value.
     *
     * @param maskpri
     * @return Previous mask value.
     */
    public int setLogmask(int maskpri) {
        int mask = logmask;
        logmask = maskpri;
        return mask;
    }

    /**
     * Close out the syslog connection.
     */
    public void close() {
        socket.close();
    }
}